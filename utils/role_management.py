import collections
from discord import Guild
from api.gametools import Result
from bot import KDRBot
from database.dto.users import User


class RoleManagement:
    async def update_kdr_role(self, bot: "KDRBot", stat: Result, guild: Guild):
        user = stat["user"]
        member = await guild.fetch_member(user.discord_id)
        if member is None:
            return

        kdr = 0
        for current in stat.get("gamemodes").values():
            current_kdr = current.get_kdr()
            if current_kdr > kdr:
                kdr = current_kdr

        kdr_roles = collections.OrderedDict(sorted(bot.config.bot.kdr_roles.items()))
        kdr_role_id = None
        for role_kdr, role_id in kdr_roles.items():
            if role_kdr < kdr:
                kdr_role_id = role_id

        if user.kdr_role_id == kdr_role_id:
            return

        if kdr_role_id is None:
            return
        new_role = await guild.fetch_role(kdr_role_id)
        if new_role is None:
            return
        await member.add_roles(*[new_role])
        roles = [
            role
            for role in member.roles
            if role.id in bot.config.bot.kdr_roles.values() and role.id != kdr_role_id
        ]
        await member.remove_roles(*roles)
        return kdr_role_id

    async def remove_kdr_roles(self, bot: KDRBot, user: User):
        guild = await bot.fetch_guild(bot.config.bot.server_id)
        if guild is None:
            return

        member = await guild.fetch_member(user.discord_id)
        if member is None:
            return

        roles = [
            role
            for role in member.roles
            if role.id in bot.config.bot.kdr_roles.values()
        ]
        await member.remove_roles(*roles)
