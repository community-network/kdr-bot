"""User management"""

import logging

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, func

from bot import KDRBot
from database.dto.users import User
from utils.role_management import RoleManagement


class Admin(commands.Cog):
    def __init__(self, bot: KDRBot):
        self.bot = bot
        self.logger = logging.getLogger("admin")

    group = app_commands.Group(
        name="admin", description="Commands meant only for admins"
    )

    async def username_autocomplete(
        self,
        _interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete usernames"""
        async with self.bot.db.create_session() as session:
            stmt = (
                select(User.username)
                .filter(func.lower(User.username).startswith(func.lower(current)))
                .limit(25)
            )
            users = await session.execute(stmt)
            return [
                app_commands.Choice(name=player, value=player)
                for player in users.scalars()
            ]

    @group.command(name="unregister", description="Unregister a user")
    @app_commands.describe(username="EA username")
    @app_commands.autocomplete(
        username=username_autocomplete,
    )
    async def register(self, interaction: discord.Interaction, username: str) -> None:
        """Register a user."""
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            stmt = (
                select(User)
                .filter(func.lower(User.username) == func.lower(username))
                .limit(1)
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                await interaction.followup.send(
                    "User not found within the db", ephemeral=True
                )
                return

            await RoleManagement().remove_kdr_roles(self.bot, user)
            await session.delete(user)
            await session.commit()
            await interaction.followup.send(
                "User has been unregistered", ephemeral=True
            )


async def setup(bot: KDRBot) -> None:
    """Setup the cog within discord.py lib"""
    await bot.add_cog(Admin(bot))
