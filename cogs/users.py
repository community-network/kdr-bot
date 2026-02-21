"""User management"""

import logging
import discord
from discord import app_commands
from discord.ext import commands

from bot import KDRBot
from database.error_handling import is_unique_violation
from utils.kd_roles import get_kd_roles
from utils.role_management import RoleManagement
from sqlalchemy.exc import IntegrityError


class Users(commands.Cog):
    def __init__(self, bot: KDRBot):
        self.bot = bot
        self.logger = logging.getLogger("users")

    @app_commands.command(name="register", description="Register a user")
    @app_commands.describe(username="EA username")
    @app_commands.guild_only()
    async def register(self, interaction: discord.Interaction, username: str) -> None:
        """Register a user."""
        async with self.bot.db.create_session() as session:
            if interaction.guild is None:
                await interaction.followup.send(
                    "Command has to be used in the server", ephemeral=True
                )
                return

            await interaction.response.defer()
            players = await self.bot.gametools_api.find_player(interaction, username)
            if len(players) <= 0:
                await interaction.followup.send("User not found", ephemeral=True)
                return
            found_player = players[0]

            stats = await self.bot.gametools_api.get_stats(found_player)
            if len(players) <= 0:
                await interaction.followup.send(
                    "No stats found for user", ephemeral=True
                )
                return

            stat = stats[0]
            kd_roles = await get_kd_roles(session, stat["user"].server_id)
            kdr_role_id = await RoleManagement().update_kdr_role(
                self.bot, stat["user"], stat["gamemodes"], kd_roles
            )

            found_player.kdr_role_id = kdr_role_id
            try:
                session.add(found_player)
                await session.commit()
            except IntegrityError as ex:
                if is_unique_violation(ex):
                    await interaction.followup.send(
                        "You are already registered within this discord!",
                        ephemeral=True,
                    )

            await interaction.followup.send("Registered", ephemeral=True)


async def setup(bot: KDRBot) -> None:
    """Setup the cog within discord.py lib"""
    await bot.add_cog(Users(bot))
