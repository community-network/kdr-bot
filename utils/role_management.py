import collections
from discord import Guild
from api.gametools import NEEDED_GAMEMODES, REDSEC_MODES
from bot import KDRBot
from database.dto.users import User
from dto.kdr import KDR


class RoleManagement:
    async def get_guild(self, bot: KDRBot, id: int):
        obj = bot.get_guild(id)
        return obj or await bot.fetch_guild(id)

    async def get_member(self, guild: Guild, id: int):
        obj = guild.get_member(id)
        return obj or await guild.fetch_member(id)

    async def get_role(self, guild: Guild, id: int):
        obj = guild.get_role(id)
        return obj or await guild.fetch_role(id)

    def get_gamemodes(self, server_mode: str):
        needed_modes = [server_mode]
        if server_mode == "Redsec":
            needed_modes = list(REDSEC_MODES.values())
        elif server_mode == "All":
            needed_modes = list(NEEDED_GAMEMODES.values())
        return needed_modes

    async def update_kdr_role(
        self,
        bot: KDRBot,
        user: User,
        stat: dict[str, KDR],
        kdr_roles: collections.OrderedDict,
        server_mode: str,
    ):
        guild = await self.get_guild(bot, user.server_id)
        if guild is None:
            return

        member = await self.get_member(guild, user.discord_id)
        if member is None:
            return

        needed_modes = self.get_gamemodes(server_mode)
        kdr_class = KDR()
        for name, current in stat.items():
            if name in needed_modes:
                kdr_class.combine(current)
        kdr = kdr_class.get_kdr()

        kdr_role_id = None
        for role_kdr, role_id in kdr_roles.items():
            if role_kdr < kdr:
                kdr_role_id = role_id

        if user.kdr_role_id == kdr_role_id:
            return

        if kdr_role_id is None:
            return
        new_role = await self.get_role(guild, kdr_role_id)
        if new_role is None:
            return
        await member.add_roles(*[new_role])
        roles = [
            role
            for role in member.roles
            if role.id in kdr_roles.values() and role.id != kdr_role_id
        ]
        await member.remove_roles(*roles)
        return kdr_role_id

    async def remove_kdr_roles(
        self,
        bot: KDRBot,
        user: User,
        kdr_roles: collections.OrderedDict,
    ):
        guild = await self.get_guild(bot, user.server_id)
        if guild is None:
            return

        member = await self.get_member(guild, user.discord_id)
        if member is None:
            return

        roles = [role for role in member.roles if role.id in kdr_roles.values()]
        await member.remove_roles(*roles)
