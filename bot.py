"""discord api connection"""

import asyncio
import collections
import logging
import os
import discord
from discord.ext import commands, tasks
from api.gametools import GametoolsApi
from config import load_config
from database.connection import DatabaseSingleton
from database.dto.users import User
from logger import setup_logger

from utils.kd_roles import get_all_kd_roles
from utils.server_settings import add_guild, has_guild
from utils.user_servers import fetch_user_servers

env_config = load_config()

logger = logging.getLogger("bot")
setup_logger(logger)


class KDRBot(commands.AutoShardedBot):
    """Bot setup class."""

    def __init__(self, *args, **kwargs):
        self.logger = logger
        self.config = env_config
        self.db = DatabaseSingleton(env_config.db)
        self.gametools_api = GametoolsApi()
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        await self.db.init_db()
        self.remove_command("help")
        await self.load_cogs()
        logger.info("Adding all servers of the bot to the db")
        self.update_kdr.start()
        async with self.db.create_session() as session:
            async for guild in self.fetch_guilds():
                if not await has_guild(session, guild.id):
                    await add_guild(session, guild, {})
                    logger.info(f'Added guild "{guild.name}"')

        logger.info("Bot started")

    async def load_cogs(self):
        for file in os.listdir(os.path.dirname(__file__) + "/cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                await bot.load_extension(f"cogs.{name}")
                self.logger.info(f"Loaded cog: {name}")

    @tasks.loop(hours=12)
    async def update_kdr(self):
        logger.info("Updating KDR roles...")
        from utils.role_management import RoleManagement  # against circular import

        async with self.db.create_session() as session:
            server_kd_roles = await get_all_kd_roles(session)
            user_servers = await fetch_user_servers(session)
            for chunk in user_servers:
                stats = await self.gametools_api.get_multiple_stats(chunk)
                for stat in stats:
                    if isinstance(stat["user"], User):
                        continue
                    for server in stat["user"].servers:
                        user = stat["user"]
                        kdr_role_id = await RoleManagement().update_kdr_role(
                            self,
                            user.to_user(server),
                            stat["gamemodes"],
                            server_kd_roles.get(
                                server.server_id, collections.OrderedDict({})
                            ),
                        )
                        if server.kdr_role_id != kdr_role_id:
                            await User(discord_id=server.discord_id).update_kdr(
                                session, kdr_role_id
                            )
        logger.info("Done updating KDR roles!")


intents = discord.Intents.default()
bot = KDRBot(command_prefix="!", intents=intents)


@bot.event
async def on_guild_join(guild: discord.Guild):
    async with bot.db.create_session() as session:
        if not await has_guild(session, guild.id):
            await add_guild(session, guild, {})
            logger.info(f'Added guild "{guild.name}"')


@bot.event
async def on_command_error(ctx, error):
    """dont give a error if a command doesn't exist"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        return
    elif isinstance(error, commands.MissingRole):
        return
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            color=0xE74C3C, description="Your not allowed to use this command"
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.NoPrivateMessage):
        embed = discord.Embed(
            color=0xE74C3C,
            description="This command can only be used within a community, not in DM",
        )
        await ctx.send(embed=embed)
    else:
        raise error


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
