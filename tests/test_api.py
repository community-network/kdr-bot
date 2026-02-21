import asyncio

from api.gametools import GametoolsApi
from database.dto.users import User


async def main():
    api = GametoolsApi()
    await api.__session_init__()
    stats = await api.get_stats(
        User(
            server_id=0,
            discord_id=0,
            username="",
            player_id=352335699,
            user_id=2411495294,
        )
    )

    kdr = 0
    for current in stats[0].get("gamemodes").values():
        current_kdr = current.get_kdr()
        if current_kdr > kdr:
            kdr = current_kdr
    print(kdr)


if __name__ == "__main__":
    asyncio.run(main())
