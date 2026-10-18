import discord
import database as db

async def is_staff(interaction: discord.Interaction) -> bool:
    user = interaction.user
    if not isinstance(user, discord.Member):
        return False
    if user.guild_permissions.administrator:
        return True
    role_id = await db.get_setting(interaction.guild_id, "staff_role")
    if role_id is None:
        return False
    return any(r.id == int(role_id) for r in user.roles)
