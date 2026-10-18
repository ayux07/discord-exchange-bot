import asyncio
import io
import discord
import database as db
from utils.checks import is_staff
from utils.transcript import build_transcript
from config import BRAND, EMBED_COLOR

async def get_ticket(channel_id: int):
    return await db.fetchone("SELECT * FROM tickets WHERE channel_id=?", (channel_id,))

async def create_ticket_channel(guild: discord.Guild, member: discord.Member,
                                name: str, topic: str | None = None) -> discord.TextChannel:
    base = dict(view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(**base),
        guild.me: discord.PermissionOverwrite(**base, manage_channels=True, embed_links=True),
    }

    staff_role_id = await db.get_setting(guild.id, "staff_role")
    if staff_role_id:
        role = guild.get_role(int(staff_role_id))
        if role:
            overwrites[role] = discord.PermissionOverwrite(**base)

    category = None
    category_id = await db.get_setting(guild.id, "ticket_category")
    if category_id:
        category = guild.get_channel(int(category_id))

    return await guild.create_text_channel(
        name=name, overwrites=overwrites, category=category, topic=topic
    )

async def claim_ticket(interaction: discord.Interaction) -> bool:
    if not await is_staff(interaction):
        await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
        return False

    changed = await db.execute(
        "UPDATE tickets SET claimed_by=? WHERE channel_id=? AND claimed_by IS NULL",
        (interaction.user.id, interaction.channel_id),
    )
    if not changed:
        await interaction.response.send_message(
            "This ticket is already claimed (or is not a ticket).", ephemeral=True
        )
        return False
    return True

class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Yes, close it", style=discord.ButtonStyle.danger)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Closing ticket...", view=None)
        await close_ticket(interaction.channel, interaction.user)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled.", view=None)

async def prompt_close(interaction: discord.Interaction):
    ticket = await get_ticket(interaction.channel_id)
    if not ticket:
        return await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)

    if not (await is_staff(interaction) or interaction.user.id == ticket["user_id"]):
        return await interaction.response.send_message(
            "Only staff or the ticket owner can close this.", ephemeral=True
        )

    await interaction.response.send_message(
        "Are you sure you want to close this ticket?", view=ConfirmCloseView(), ephemeral=True
    )

async def close_ticket(channel: discord.TextChannel, closer: discord.abc.User):
    guild = channel.guild
    ticket = await get_ticket(channel.id)

    data = await build_transcript(channel)
    filename = f"transcript-{channel.name}.html"

    if ticket:
        await db.execute(
            "UPDATE tickets SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE id=?",
            (ticket["id"],),
        )

    log_id = await db.get_setting(guild.id, "transcript_channel")
    if log_id:
        log_channel = guild.get_channel(int(log_id))
        if log_channel:
            embed = discord.Embed(title="Ticket Closed", color=EMBED_COLOR)
            embed.add_field(name="Channel", value=channel.name)
            embed.add_field(name="Closed by", value=closer.mention)
            if ticket:
                embed.add_field(name="Opened by", value=f"<@{ticket['user_id']}>")
                embed.add_field(name="Claimed by",
                                value=f"<@{ticket['claimed_by']}>" if ticket["claimed_by"] else "Nobody")
            await log_channel.send(
                embed=embed, file=discord.File(io.BytesIO(data), filename=filename)
            )

    if ticket:
        member = guild.get_member(ticket["user_id"])
        if member:
            try:
                await member.send(
                    f"Your ticket in **{guild.name}** was closed. Transcript attached.",
                    file=discord.File(io.BytesIO(data), filename=filename),
                )
            except discord.HTTPException:
                pass

    await asyncio.sleep(5)
    await channel.delete(reason=f"Ticket closed by {closer}")
