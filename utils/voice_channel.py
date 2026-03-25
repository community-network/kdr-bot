import discord

async def create_voice_channel(guild: discord.Guild, category: discord.CategoryChannel, kd_role: dict, position: int | None = None):
    voice_channel = await category.create_voice_channel(kd_role.get("channel_name"), position=position)
    own_role = guild.get_role(kd_role.get("role_id"))
    overwrites = { 
        guild.default_role: discord.PermissionOverwrite(connect=False),
        own_role: discord.PermissionOverwrite(connect=True)
    }
    for lower_role in kd_role.get("lower_roles", []):
        role = guild.get_role(lower_role.get("role_id"))
        overwrites[role] = discord.PermissionOverwrite(connect=True)
    await voice_channel.edit(overwrites=overwrites)
    return voice_channel