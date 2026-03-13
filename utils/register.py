import discord
from sqlalchemy.exc import IntegrityError

from bot import KDRBot
from database.error_handling import is_unique_violation
from utils.kd_roles import get_kd_roles
from utils.role_management import RoleManagement
from utils.server_settings import send_log


async def register(bot: KDRBot, interaction: discord.Interaction, username: str):
    async with bot.db.create_session() as session:
        players = await bot.gametools_api.find_player(interaction, username)
        if len(players) <= 0:
            msg = "User not found"
            await interaction.followup.send(msg, ephemeral=True)
            await send_log(
                bot,
                session,
                interaction.guild_id,
                f'{interaction.user.mention} just tried to register with EA ID: "{username}", {msg}',
            )
            return
        found_player = players[0]

        stats = await bot.gametools_api.get_stats(found_player)
        if len(players) <= 0:
            msg = "No stats found for user"
            await interaction.followup.send(msg, ephemeral=True)
            await send_log(
                bot,
                session,
                interaction.guild_id,
                f'{interaction.user.mention} just tried to register with EA ID: "{username}", {msg}',
            )
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
            await send_log(
                bot,
                session,
                interaction.guild_id,
                f'{interaction.user.mention} just registered with EA ID: "{username}"',
            )
        except IntegrityError as ex:
            await session.rollback()
            if is_unique_violation(ex):
                await interaction.followup.send(
                    "You are already registered within this discord!",
                    ephemeral=True,
                )
                await send_log(
                    bot,
                    session,
                    interaction.guild_id,
                    f'{interaction.user.mention} just tried to register with EA ID: "{username}", but is already registered',
                )
                return

        await interaction.followup.send("Registered", ephemeral=True)
