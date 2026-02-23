"""User management"""

import logging
import os
import sys

import discord
from discord import Role, app_commands
from discord.ext import commands
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError

from bot import KDRBot
from database.dto.kd_roles import KDRole
from database.dto.users import User
from database.error_handling import is_unique_violation
from utils.kd_roles import get_kd_roles
from utils.register import register
from utils.role_management import RoleManagement


class RegisterModal(discord.ui.Modal, title="Register your EA account"):
    def __init__(self, bot: KDRBot):
        self.bot = bot
        super().__init__()

    username = discord.ui.TextInput(
        label="What is your EA id",
        style=discord.TextStyle.short,
        max_length=500,
        placeholder="test",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction[KDRBot]) -> None:
        await interaction.response.defer()
        await register(self.bot, interaction, self.username.value)


class RegisterView(discord.ui.View):
    def __init__(self, bot: KDRBot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Register",
        custom_id="register_user",
        style=discord.ButtonStyle.primary,
    )
    async def verify_callback(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(RegisterModal(self.bot))


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
    @app_commands.guild_only()
    @app_commands.autocomplete(
        username=username_autocomplete,
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def unregister(self, interaction: discord.Interaction, username: str) -> None:
        """Unregister a user."""
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            stmt = (
                select(User)
                .filter(
                    and_(
                        func.lower(User.username) == func.lower(username),
                        User.server_id == interaction.guild_id,
                    )
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                await interaction.followup.send(
                    "User not found within the db", ephemeral=True
                )
                return
            kd_roles = await get_kd_roles(session, user.server_id)
            await RoleManagement().remove_kdr_roles(self.bot, user, kd_roles)
            await session.delete(user)
            await session.commit()
            await interaction.followup.send(
                "User has been unregistered", ephemeral=True
            )

    kdroles_group = app_commands.Group(
        name="kdroles", description="Manage kdroles", parent=group
    )

    @kdroles_group.command(name="add", description="Add a KD role within the server")
    @app_commands.describe(role="A KD-role", kd="Minimum kd needed for the role")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_kd_role(
        self, interaction: discord.Interaction, role: Role, kd: float
    ) -> None:
        """Add a KD role"""
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            new_role = KDRole(
                server_id=interaction.guild_id, role_id=role.id, kd_amount=kd
            )

            try:
                session.add(new_role)
                await session.commit()
            except IntegrityError as ex:
                if is_unique_violation(ex):
                    await interaction.followup.send(
                        "The KD role already exists",
                        ephemeral=True,
                    )

            await interaction.followup.send(
                "KD-role added, users will be attached on next kd-check",
                ephemeral=True,
            )

    @kdroles_group.command(
        name="list", description="List the KD roles within the server"
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def list_kd_roles(self, interaction: discord.Interaction) -> None:
        """List the KD roles of a server"""
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            stmt = select(KDRole).filter(KDRole.server_id == interaction.guild_id)
            result = await session.execute(stmt)
            description = ""

            for role in result.scalars():
                description += f"{role.kd_amount:.2f} - <@&{role.role_id}>\n"

            embed = discord.Embed(title="Current KD roles", description=description)
            await interaction.followup.send(embed=embed, ephemeral=True)

    @kdroles_group.command(
        name="remove", description="Remove a KD role within the server"
    )
    @app_commands.describe(role="A KD-role")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_kd_role(
        self, interaction: discord.Interaction, role: Role
    ) -> None:
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            stmt = (
                select(KDRole)
                .filter(
                    and_(
                        KDRole.server_id == interaction.guild_id,
                        KDRole.role_id == role.id,
                    )
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            kd_role = result.scalar_one_or_none()

            if kd_role is None:
                await interaction.followup.send(
                    "Role does not have a KD attached", ephemeral=True
                )
                return

            await session.delete(kd_role)
            await session.commit()
            await interaction.followup.send("KD-role has been removed", ephemeral=True)

    kdroles_group = app_commands.Group(
        name="generate", description="Generate a message", parent=group
    )

    @kdroles_group.command(name="register", description="Generate the register button")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def generate_register(self, interaction: discord.Interaction) -> None:
        """Generate the register button"""
        embed = discord.Embed(
            title="Register with your EA account to get your KD-role",
        )
        await interaction.response.send_message(
            embed=embed, view=RegisterView(self.bot)
        )


async def setup(bot: KDRBot) -> None:
    """Setup the cog within discord.py lib"""
    bot.add_view(RegisterView(bot))
    await bot.add_cog(Admin(bot))
