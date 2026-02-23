import discord
from sqlalchemy.exc import IntegrityError

from bot import KDRBot
from database.error_handling import is_unique_violation
from utils.kd_roles import get_kd_roles
from utils.role_management import RoleManagement


async def register(bot: KDRBot, interaction: discord.Interaction, username: str):
    async with bot.db.create_session() as session:
        players = await bot.gametools_api.find_player(interaction, username)
        if len(players) <= 0:
            await interaction.followup.send("User not found", ephemeral=True)
            return
        found_player = players[0]

        stats = await bot.gametools_api.get_stats(found_player)
        if len(players) <= 0:
            await interaction.followup.send("No stats found for user", ephemeral=True)
            return

        stat = stats[0]
        kd_roles = await get_kd_roles(session, stat["user"].server_id)
        kdr_role_id = await RoleManagement().update_kdr_role(
            bot, stat["user"], stat["gamemodes"], kd_roles
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
                return

        await interaction.followup.send("Registered", ephemeral=True)
