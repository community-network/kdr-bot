import json
from typing import TypedDict, overload

import aiohttp
from discord import Interaction

from database.dto.users import User
from dto.kdr import KDR
from dto.user_servers import UserServers

ENDPOINT = "https://api.gametools.network/"
NEEDED_FIELDS = ["human_kills_total", "deaths_total"]
REDSEC_MODES = {
    "GraniteDuo0": "Redsec Duo",
    "GraniteSquad0": "Redsec Squad",
    "GraniteSolo0": "Redsec Solo",
}
NEEDED_GAMEMODES = {
    "MP_Escalation0": "Escalation",
    "MP_TeamDM0": "Team deathmatch",
    "GraniteGauntlet0": "Gauntlet",
    "GraniteSquad0": "Redsec Squad",
    "GraniteDuo0": "Redsec Duo",
    "GraniteSolo0": "Redsec Solo",
    "MP_KOTH0": "King of the Hill",
    "MP_Domination0": "Domination",
    "Conquest0": "Conquest",
    "MP_SquadDM0": "Squad deathmatch",
    "Breakthrough0": "Breakthrough",
    "Rush0": "Rush",
    "ModBuilderCustom0": "Portal",
}


class ServerResult(TypedDict):
    user: UserServers
    gamemodes: dict[str, KDR]


class Result(TypedDict):
    user: User
    gamemodes: dict[str, KDR]


class GametoolsApi:
    session: aiohttp.ClientSession

    @overload
    async def read_stats(
        self, users: list[UserServers], data: dict
    ) -> list[ServerResult]: ...
    @overload
    async def read_stats(self, users: list[User], data: dict) -> list[Result]: ...

    async def read_stats(self, users, data):
        db_users = {str(user.player_id): user for user in users}
        results = []
        for player in data.get("playerStats", []):
            current_player = player.get("player", {"personaId": 0})
            current_result: Result = {
                "user": db_users.get(current_player.get("personaId", 0), User()),
                "gamemodes": {v: KDR() for _, v in NEEDED_GAMEMODES.items()},
            }
            for category in player.get("categories", []):
                cat_fields = category.get("catFields") or []

                for item in cat_fields:
                    item_name = item.get("name")
                    if item_name not in NEEDED_FIELDS:
                        continue

                    item_value = item.get("value")

                    fields: list[dict] = item.get("fields", [])
                    if not fields:
                        continue

                    game_mode = None
                    season = None
                    is_global = False

                    for f in fields:
                        fname = f.get("name")
                        if fname == "GameMode":
                            game_mode = f.get("value", "")
                        elif fname == "Season":
                            season = f.get("value", "")
                        elif fname == "global":
                            is_global = True
                    if is_global or season is None or game_mode not in NEEDED_GAMEMODES:
                        continue

                    if (
                        current_result["gamemodes"].get(
                            NEEDED_GAMEMODES.get(game_mode, "")
                        )
                        is not None
                    ):
                        if item_name == "human_kills_total":
                            current_result["gamemodes"][
                                NEEDED_GAMEMODES.get(game_mode, "")
                            ].kills += item_value
                        if item_name == "deaths_total":
                            current_result["gamemodes"][
                                NEEDED_GAMEMODES.get(game_mode, "")
                            ].deaths += item_value
            results.append(current_result)
        return results

    async def __session_init__(self):
        self.session = aiohttp.ClientSession()

    async def find_player(self, interaction: Interaction, username: str) -> list[User]:
        async with self.session.get(
            ENDPOINT + "bf6/player", params={"name": username}
        ) as r:
            res = await r.json()
            if r.status == 200 or res is not None:
                players = res.get("results", [])
                return [
                    User(
                        server_id=interaction.guild_id,
                        discord_id=interaction.user.id,
                        username=username,
                        player_id=int(player.get("personaId", "")),
                        user_id=int(player.get("nucleusId", "")),
                    )
                    for player in players
                    if (
                        player.get("username", "").lower() == username.lower()
                        or player.get("displayName", "").lower() == username.lower()
                    )
                    and len(player.get("personaId", "")) > 0
                    and len(player.get("nucleusId", "")) > 0
                ]
            return []

    async def get_stats(self, user: User):
        async with self.session.get(
            ENDPOINT + "bf6/stats",
            params={
                "playerid": user.player_id,
                "nucleus_id": user.user_id,
                "raw": "true",
            },
        ) as r:
            result = await r.json()
            return await self.read_stats([user], result)

    async def get_multiple_stats(self, multiple_users: list[UserServers]):
        payload = [
            {"player_id": user.player_id, "user_id": user.user_id, "platform": "pc"}
            for user in multiple_users
        ]
        async with self.session.post(
            ENDPOINT + "bf6/multiple", data=json.dumps(payload), params={"raw": "true"}
        ) as r:
            result = await r.json()
            return await self.read_stats(multiple_users, result)
