"""discord api connection"""

import asyncio
import collections
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os
import discord
from discord.ext import commands, tasks
from api.gametools import GametoolsApi
from config import load_config
from database.connection import DatabaseSingleton
from database.dto.users import User
from logger import setup_logger

from utils.kd_roles import get_all_kd_roles, get_channel_kd_roles
from utils.match_history import remove_old_items
from utils.server_settings import add_guild, get_all_guilds_mode, has_guild, has_guild_category
from utils.user_servers import fetch_user_servers
from utils.voice_channel import create_voice_channel
from utils.voice_channels import add_voice_channel, get_role_voice_channels, get_voice_channel, remove_voice_channel

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
            server_mode = await get_all_guilds_mode(session)
            user_servers = await fetch_user_servers(session)
            for chunk in user_servers:
                try:
                    stats = await self.gametools_api.get_multiple_stats(session, chunk)
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
                                server_mode.get(server.server_id, "Redsec"),
                            )
                            if server.kdr_role_id != kdr_role_id:
                                await User(discord_id=server.discord_id).update_kdr(
                                    session, kdr_role_id
                                )
                except Exception as e:
                    logger.info(f"Group skipped: {e}")
                    
            logger.info("Done updating KDR roles!")
            await remove_old_items(session)


intents = discord.Intents.default()
bot = KDRBot(command_prefix="!", intents=intents)


async def get_channels_in_db(session: AsyncSession, member: discord.Member, category: discord.CategoryChannel, kdr_role_id: int):
    db_voice_channels = await get_role_voice_channels(session, member.guild.id, kdr_role_id)
    return [channel for channel in category.voice_channels if channel.id in db_voice_channels]

async def on_voice_channel_join(session: AsyncSession, member: discord.Member, after: discord.VoiceState):
    if not await has_guild_category(session, member.guild.id, after.channel.category_id):
        return
    
    db_channel = await get_voice_channel(session,  member.guild.id, after.channel.id)
    if db_channel is None: 
        return
    
    category = after.channel.category
    channels_in_db = await get_channels_in_db(session, member, category, db_channel.kdr_role_id)

    total_empty_channels = 0
    for channel in channels_in_db:
        if len(channel.members) == 0:
            total_empty_channels += 1

    if total_empty_channels == 0:
        kd_role = await get_channel_kd_roles(session, member.guild.id, db_channel.kdr_role_id)
        voice_channel = await create_voice_channel(member.guild, category, kd_role, after.channel.position)
        await add_voice_channel(session, member.guild.id, voice_channel.id, db_channel.kdr_role_id)

async def on_voice_channel_leave(session: AsyncSession, member: discord.Member, before: discord.VoiceState):
    if not await has_guild_category(session, member.guild.id, before.channel.category_id):
        return
    
    db_channel = await get_voice_channel(session,  member.guild.id, before.channel.id)
    if db_channel is None:
        return

    category = before.channel.category
    channels_in_db = await get_channels_in_db(session, member, category, db_channel.kdr_role_id)

    empty_channels = 0
    for channel in reversed(channels_in_db):
        total_users = len(channel.members)
        if empty_channels > 0 and total_users <= 0:
            await remove_voice_channel(session, member.guild.id, channel.id)
            await channel.delete()
        elif len(channel.members) <= 0:
            empty_channels += 1


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState | None, after: discord.VoiceState | None):
    async with bot.db.create_session() as session:
        if member.guild.id is None:
            return
        if (before.channel is None and after.channel is not None): # join
            await on_voice_channel_join(session, member, after)

        if before.channel is not None and after.channel is None: # leave
            await on_voice_channel_leave(session, member, before)

        if before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            await on_voice_channel_leave(session, member, before)
            await on_voice_channel_join(session, member, after)

                
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
