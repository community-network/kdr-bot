"""User management"""

import logging
from typing import Optional
import discord
from discord import Role, app_commands
from discord.ext import commands
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError

from bot import KDRBot
from database.dto.kd_roles import KDRole
from database.dto.users import User
from database.error_handling import is_unique_violation
from utils.kd_roles import get_channel_kd_roles, get_kd_roles, update_kd_role
from utils.register import register
from utils.role_management import RoleManagement
from utils.server_settings import get_guild, update_guild
from utils.users import get_users_csv
from utils.voice_channel import create_voice_channel
from utils.voice_channels import add_voice_channel


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
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete usernames"""
        async with self.bot.db.create_session() as session:
            stmt = (
                select(User.username)
                .filter(
                    and_(
                        func.lower(User.username).startswith(func.lower(current)),
                        User.server_id == interaction.guild_id,
                    )
                )
                .limit(25)
            )
            users = await session.execute(stmt)
            return [
                app_commands.Choice(name=player, value=player)
                for player in users.scalars()
            ]


    @group.command(name="export", description="Export all registered users")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def export_registered_users(self, interaction: discord.Interaction) -> None:
        """Export all registered users"""
        await interaction.response.defer()
        if interaction.guild is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            total, registered_users = await get_users_csv(session, interaction.guild_id)
            if total <= 0:
                await interaction.followup.send("There are currently no registered users", ephemeral=True)
                return
            await interaction.followup.send("Registered users:", ephemeral=True, file=registered_users)


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

    @group.command(
        name="mode", description="Change the mode to track (defaults to redsec)"
    )
    @app_commands.describe(mode="Name of the mode (defaults to redsec)")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        mode=[
            # specific gamemode
            app_commands.Choice(name="Escalation", value="Escalation"),
            app_commands.Choice(name="Team deathmatch", value="Team deathmatch"),
            app_commands.Choice(name="Gauntlet", value="Gauntlet"),
            app_commands.Choice(name="Redsec Squad", value="Redsec Squad"),
            app_commands.Choice(name="Redsec Solo", value="Redsec Solo"),
            app_commands.Choice(name="King of the Hill", value="King of the Hill"),
            app_commands.Choice(name="Redsec Duo", value="Redsec Duo"),
            app_commands.Choice(name="Domination", value="Domination"),
            app_commands.Choice(name="Conquest", value="Conquest"),
            app_commands.Choice(name="Squad deathmatch", value="Squad deathmatch"),
            app_commands.Choice(name="Breakthrough", value="Breakthrough"),
            app_commands.Choice(name="Rush", value="Rush"),
            app_commands.Choice(name="Portal", value="Portal"),
            # combined
            app_commands.Choice(name="Redsec", value="Redsec"),
            app_commands.Choice(name="All", value="All"),
        ],
    )
    async def set_mode(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
    ) -> None:
        """Change the game to track"""
        await interaction.response.defer()
        if interaction.guild is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            await update_guild(session, interaction.guild, {"mode": mode.value})
        await interaction.followup.send(
            f'Set the logging channel to "{mode.value}"', ephemeral=True
        )

    kdroles_group = app_commands.Group(
        name="kdroles", description="Manage kdroles", parent=group
    )

    @kdroles_group.command(name="add", description="Add a KD role within the server")
    @app_commands.describe(role="A KD-role", kd="Minimum kd needed for the role", channel_name="The name of the channel it will autocreate for the kdr-ratio")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_kd_role(
        self, interaction: discord.Interaction, role: Role, kd: float, channel_name: Optional[str]
    ) -> None:
        """Add a KD role"""
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            new_role = KDRole(
                server_id=interaction.guild_id, role_id=role.id, kd_amount=kd, channel_name=channel_name
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
        name="update", description="Update a KD role within the server"
    )
    @app_commands.describe(role="A KD-role", channel_name="Name of the autogenerated KD-roles channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def update_kd_role(
        self, interaction: discord.Interaction, role: Role, channel_name: str
    ) -> None:
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            await update_kd_role(session, interaction.guild_id, role.id, {"channel_name":channel_name })
            await interaction.followup.send("KD-role has been updated", ephemeral=True)


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

    generate_group = app_commands.Group(
        name="generate", description="Generate a message", parent=group
    )

    @generate_group.command(name="register", description="Generate the register button")
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


    @generate_group.command(name="initial-channel", description="Generate the initial kd channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def generate_initial_channel(self, interaction: discord.Interaction) -> None:
        """Generate the initial kd channel"""
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            guild_settings = await get_guild(session, interaction.guild_id)
            if guild_settings is None:
                await interaction.followup.send("No server settings found")
            if guild_settings.category_id is None:
                await interaction.followup.send("Category is not set")
            
            for category in interaction.guild.categories:
                if guild_settings.category_id == category.id:
                    kd_roles = await get_channel_kd_roles(session, interaction.guild_id)
                    for kd_role in kd_roles:
                        try:
                            voice_channel = await create_voice_channel(interaction.guild, category, kd_role)
                        except discord.DiscordException as e:
                            await interaction.followup.send(f"Failed to create the initial voice channel: {e}")
                            continue
                        await add_voice_channel(session, interaction.guild_id, voice_channel.id, kd_role.get("role_id"))
                    await interaction.followup.send("Created the initial voice channels")                        
                    return
            
        await interaction.followup.send("The set category is not found within the server")

        
    logging_group = app_commands.Group(
        name="log", description="Manage the logging", parent=group
    )

    @logging_group.command(
        name="channel",
        description="Set the channel to log new registration attempts to",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        """Set the channel to log new registration attempts to"""
        await interaction.response.defer()
        if interaction.guild is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            await update_guild(
                session, interaction.guild, {"log_channel_id": channel.id}
            )
        await interaction.followup.send(
            f'Set the logging channel to "{channel.name}"', ephemeral=True
        )


    set_group = app_commands.Group(
        name="set", description="Set a setting", parent=group
    )

    @set_group.command(name="category", description="Set the used category")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_category(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        """Set the used category"""
        await interaction.response.defer()
        if interaction.guild is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            await update_guild(
                session, interaction.guild, {"category_id": category.id}
            )
        await interaction.followup.send(
            f'Set the category channel to "{category.name}"', ephemeral=True
        )



async def setup(bot: KDRBot) -> None:
    """Setup the cog within discord.py lib"""
    bot.add_view(RegisterView(bot))
    await bot.add_cog(Admin(bot))
