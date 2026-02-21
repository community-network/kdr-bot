"""User management"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot import KDRBot
from utils.role_management import RoleManagement


class Users(commands.Cog):
    def __init__(self, bot: KDRBot):
        self.bot = bot
        self.logger = logging.getLogger("users")

    @app_commands.command(name="register", description="Register a user")
    @app_commands.describe(username="EA username")
    async def register(self, interaction: discord.Interaction, username: str) -> None:
        """Register a user."""
        async with self.bot.db.create_session() as session:
            if (
                interaction.guild is None
                or interaction.guild_id != self.bot.config.bot.server_id
            ):
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

            kdr_role_id = await RoleManagement().update_kdr_role(
                self.bot, stats[0], interaction.guild
            )

            found_player.kdr_role_id = kdr_role_id

            session.add(found_player)
            await session.commit()

            await interaction.followup.send("Registered", ephemeral=True)


async def setup(bot: KDRBot) -> None:
    """Setup the cog within discord.py lib"""
    await bot.add_cog(Users(bot))
