# utils/checks.py
import traceback
import discord
from discord.ext import commands
import database as db


async def role_ids_for(guild_id: int, *kinds: str) -> list[int]:
    """Role IDs configured for any of the given kinds."""
    marks = ",".join("?" for _ in kinds)   # only '?' characters are inserted, never user input
    rows = await db.fetchall(
        f"SELECT DISTINCT role_id FROM role_perms WHERE guild_id=? AND kind IN ({marks})",
        (guild_id, *kinds),
    )
    return [r["role_id"] for r in rows]


async def member_has_kind(member, *kinds: str) -> bool:
    """True for server admins, or members holding a role configured for any of these kinds."""
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    ids = set(await role_ids_for(member.guild.id, *kinds))
    return any(r.id in ids for r in member.roles)


def require(*kinds: str):
    """Command decorator: only allow members with one of these role kinds (admins always pass)."""
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        if await member_has_kind(ctx.author, *kinds):
            return True
        raise commands.CheckFailure("You don't have permission to use this command.")
    return commands.check(predicate)


class SafeModal(discord.ui.Modal):
    """Modal that reports errors to the user instead of failing silently."""
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        traceback.print_exception(type(error), error, error.__traceback__)
        msg = "Something went wrong. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
