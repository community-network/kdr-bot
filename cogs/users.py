"""User management"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import and_, select

from bot import KDRBot
from database.dto.users import User
from utils.register import register


class Users(commands.Cog):
    def __init__(self, bot: KDRBot):
        self.bot = bot
        self.logger = logging.getLogger("users")

    @app_commands.command(name="register", description="Register a user")
    @app_commands.describe(username="EA username")
    @app_commands.guild_only()
    async def register(self, interaction: discord.Interaction, username: str) -> None:
        """Register a user."""
        await interaction.response.defer()
        if interaction.guild is None:
            await interaction.followup.send(
                "Command has to be used in the server", ephemeral=True
            )
            return

        await register(self.bot, interaction, username)

    @app_commands.command(name="kdr", description="Get your current kdr")
    @app_commands.guild_only()
    async def kdr(self, interaction: discord.Interaction) -> None:
        """Get current kdr"""
        async with self.bot.db.create_session() as session:
            await interaction.response.defer()
            stmt = (
                select(User)
                .filter(
                    and_(
                        User.discord_id == interaction.user.id,
                        User.server_id == interaction.guild_id,
                    )
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                await interaction.followup.send("Please register first", ephemeral=True)
                return

            stats = await self.bot.gametools_api.get_stats(user)
            embed = discord.Embed(
                title="Current KDR info",
                description=f"Current rank: {f'<@&{user.kdr_role_id}>' if user.kdr_role_id is not None else 'N/A'}",
            )
            embed.add_field(
                name="Player",
                value=f"<@{user.discord_id}> ({user.username})",
                inline=False,
            )
            for gamemode, kdr in stats[0]["gamemodes"].items():
                embed.add_field(
                    name=gamemode,
                    value=f"kills: {kdr.kills}\ndeaths: {kdr.deaths}\nK/D: {kdr.get_kdr()}",
                )
            await interaction.followup.send(embed=embed)


async def setup(bot: KDRBot) -> None:
    """Setup the cog within discord.py lib"""
    await bot.add_cog(Users(bot))
