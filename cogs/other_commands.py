"""Non-grouped commands"""

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

from bot import KDRBot


class OtherCommands(commands.Cog):
    """Other commands"""

    def __init__(self, bot: KDRBot):
        self.bot = bot

    @app_commands.command(name="help", description="See more info about the bot")
    async def help_command(self, interaction: discord.Interaction):
        """Main help command"""
        await interaction.response.defer()
        embed = discord.Embed(
            color=0xFFA500,
            title="Help for the KD-role manager",
            description='Use "/admin kdroles" to manage the attached roles and set their minimum KD to get that specific role. If you hit the minimum for the next KD role, it will remove the old and set it to the higher role. It checks all users that register with "/register \'ea-username\'" every 12 hours to update their roles.\nIf you need further assistance with the bot. You can ask it here: https://discord.gg/bf6ranked',
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: KDRBot) -> None:
    """Setup the cog within discord.py lib"""
    await bot.add_cog(OtherCommands(bot))
