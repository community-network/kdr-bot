"""discord api connection"""

import asyncio
import logging
import os
import discord
from discord.ext import commands, tasks
from sqlalchemy import select
from api.gametools import GametoolsApi
from config import load_config
from database.connection import DatabaseSingleton
from database.dto.users import User
from logger import setup_logger

env_config = load_config()

logger = logging.getLogger("bot")
setup_logger(logger)


class KDRBot(commands.AutoShardedBot):
    """Bot setup class."""

    def __init__(self, *args, **kwargs):
        self.logger = logger
        self.config = env_config
        self.db = DatabaseSingleton(env_config.bot.db_url)
        self.gametools_api = GametoolsApi()
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        await self.db.init_db()
        self.remove_command("help")
        await self.load_cogs()
        logger.info("bot started")
        self.update_kdr.start()

    async def load_cogs(self):
        for file in os.listdir(os.path.dirname(__file__) + "/cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                await bot.load_extension(f"cogs.{name}")
                self.logger.info(f"Loaded cog: {name}")

    @tasks.loop(hours=12)
    async def update_kdr(self):
        logger.info("updating KDR roles...")
        from utils.role_management import RoleManagement  # against circular import

        async with self.db.create_session() as session:
            guild = await bot.fetch_guild(bot.config.bot.server_id)
            if guild is None:
                return

            stmt = select(User)
            res = await session.execute(stmt)
            chunked_users = res.scalars().partitions(10)
            for chunk in chunked_users:
                stats = await self.gametools_api.get_multiple_stats(list(chunk))
                for stat in stats:
                    kdr_role_id = await RoleManagement().update_kdr_role(
                        self, stat, guild
                    )
                    user = stat["user"]
                    if user.kdr_role_id != kdr_role_id:
                        await user.update_kdr(session, kdr_role_id)
        logger.info("Done updating KDR roles!")


intents = discord.Intents.default()
intents.members = True
bot = KDRBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """After bot is logged into discord"""
    await bot.tree.sync()


async def main() -> None:
    async with bot:
        await bot.gametools_api.__session_init__()
        await bot.start(env_config.bot.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())

    # After bot is shut down or crashes
    asyncio.run(bot.db.close_async())
