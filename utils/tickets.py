# utils/tickets.py
import asyncio
import io
import re
import discord
import database as db
from config import EMBED_COLOR, EX_TYPES
from utils.checks import member_has_kind, role_ids_for
from utils.transcript import build_transcript
from utils.calc import get_tax_percent

# which role kind handles which ticket kind
KIND_ROLE = {"exchange": "exchanger", "support": "support", "apply": "application"}

# role/user pings are allowed only where we explicitly pass this
PINGS = discord.AllowedMentions(roles=True, users=True, everyone=False)


# ------------------------------------------------------------------ basics
async def get_ticket(channel_id: int):
    return await db.fetchone("SELECT * FROM tickets WHERE channel_id=?", (channel_id,))


async def existing_open(guild_id: int, user_id: int, kind: str):
    return await db.fetchone(
        "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? AND kind=? AND status='open'",
        (guild_id, user_id, kind),
    )


async def staff_pings(guild: discord.Guild, kind: str) -> str:
    ids = await role_ids_for(guild.id, KIND_ROLE[kind])
    return " ".join(f"<@&{i}>" for i in ids)


def clean_name(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", text.lower())[:40] or "staff"


async def rename_channel(channel: discord.TextChannel, name: str):
    """Renames can be rate-limited (2 per 10 min), so failures are ignored."""
    try:
        await channel.edit(name=name)
    except discord.HTTPException:
        pass


# ------------------------------------------------------------ create ticket
async def create_ticket_channel(guild, member, name, kind, topic=None) -> discord.TextChannel:
    """Private channel for: the member, the roles for this ticket kind, manager roles, and the bot."""
    base = dict(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(**base),
        guild.me: discord.PermissionOverwrite(**base, embed_links=True, manage_channels=True),
    }
    for rid in await role_ids_for(guild.id, KIND_ROLE[kind], "manager"):
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(**base)

    category = None
    category_id = await db.get_setting(guild.id, "ticket_category")
    if category_id:
        found = guild.get_channel(int(category_id))
        if isinstance(found, discord.CategoryChannel):
            category = found

    return await guild.create_text_channel(name=name, overwrites=overwrites, category=category, topic=topic)


async def new_ticket(guild, member, kind: str, slug: str, fields: dict):
    """
    1) insert a DB row (to get the ticket number)
    2) create the channel named <slug>-<0000>
    3) store the channel id
    Returns (ticket_id, channel). Raises discord.HTTPException if the channel cannot be created.
    """
    cols = {"guild_id": guild.id, "channel_id": 0, "user_id": member.id, "kind": kind, **fields}
    names = ", ".join(cols)                      # column names come from our own code only
    marks = ", ".join("?" for _ in cols)
    ticket_id = await db.insert(f"INSERT INTO tickets ({names}) VALUES ({marks})", tuple(cols.values()))

    base_name = f"{slug}-{ticket_id:04d}"
    try:
        channel = await create_ticket_channel(
            guild, member, base_name, kind, topic=f"{kind} ticket #{ticket_id} for {member}"
        )
    except discord.HTTPException:
        await db.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
        raise

    await db.execute("UPDATE tickets SET channel_id=?, base_name=? WHERE id=?",
                     (channel.id, base_name, ticket_id))
    return ticket_id, channel


# ------------------------------------------------------ refresh the buttons
async def refresh_ticket_message(channel: discord.TextChannel, ticket_id: int):
    """Rebuild the button row from the database (Claimed / MM Requested / decisions)."""
    from utils.ticket_views import VIEW_FOR_KIND       # lazy import avoids a circular import
    t = await db.fetchone("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not t or not t["message_id"]:
        return
    view = VIEW_FOR_KIND[t["kind"]]()
    for child in view.children:
        cid = getattr(child, "custom_id", "") or ""
        if cid.endswith(":claim") and t["claimed_by"]:
            child.label, child.disabled = "Claimed", True
        elif cid.endswith(":mm") and t["mm_requested"]:
            child.label, child.disabled = "MM Requested", True
        elif cid.endswith((":accept", ":deny")) and t["decision"]:
            child.disabled = True
    try:
        message = await channel.fetch_message(t["message_id"])
        await message.edit(view=view)
    except discord.HTTPException:
        pass


# ------------------------------------------------------------ claim / unclaim
async def do_claim(member: discord.Member, channel: discord.TextChannel):
    t = await get_ticket(channel.id)
    if not t or t["status"] != "open":
        return False, "This is not an open ticket."
    if not await member_has_kind(member, KIND_ROLE[t["kind"]]):
        return False, "You don't have the role needed to claim this type of ticket."

    # atomic: only succeeds if nobody claimed it yet
    changed = await db.execute(
        "UPDATE tickets SET claimed_by=? WHERE id=? AND claimed_by IS NULL", (member.id, t["id"])
    )
    if not changed:
        return False, "This ticket is already claimed."

    asyncio.create_task(rename_channel(channel, f"claimed-{clean_name(member.name)}"))
    await refresh_ticket_message(channel, t["id"])
    return True, ""


async def do_unclaim(member: discord.Member, channel: discord.TextChannel):
    t = await get_ticket(channel.id)
    if not t or t["status"] != "open":
        return False, "This is not an open ticket."
    if not t["claimed_by"]:
        return False, "This ticket isn't claimed."
    if t["completed"]:
        return False, "This deal is already completed."
    if t["claimed_by"] != member.id and not await member_has_kind(member, "manager"):
        return False, "Only the person who claimed it (or a manager) can unclaim."

    await db.execute("UPDATE tickets SET claimed_by=NULL WHERE id=?", (t["id"],))
    if t["base_name"]:
        asyncio.create_task(rename_channel(channel, t["base_name"]))
    await refresh_ticket_message(channel, t["id"])
    return True, ""


async def claim_button(interaction: discord.Interaction):
    await interaction.response.defer()
    ok, msg = await do_claim(interaction.user, interaction.channel)
    if ok:
        await interaction.followup.send(f"✅ Ticket claimed by {interaction.user.mention}.")
    else:
        await interaction.followup.send(msg, ephemeral=True)


# ----------------------------------------------------------- request middleman
async def request_mm(interaction: discord.Interaction):
    t = await get_ticket(interaction.channel_id)
    if not t or t["status"] != "open":
        return await interaction.response.send_message("This is not an open ticket.", ephemeral=True)

    allowed = interaction.user.id == t["user_id"] or await member_has_kind(
        interaction.user, KIND_ROLE[t["kind"]]
    )
    if not allowed:
        return await interaction.response.send_message("Only the client or staff can request a middleman.", ephemeral=True)

    mm_roles = await role_ids_for(interaction.guild_id, "middleman")
    if not mm_roles:
        return await interaction.response.send_message(
            "No middleman roles are configured. An admin must run `,addrole middleman @role`.", ephemeral=True
        )

    changed = await db.execute(
        "UPDATE tickets SET mm_requested=1 WHERE id=? AND mm_requested=0", (t["id"],)
    )
    if not changed:
        return await interaction.response.send_message("A middleman was already requested.", ephemeral=True)

    await interaction.response.defer()
    pings = []
    for rid in mm_roles:
        role = interaction.guild.get_role(rid)
        if role:
            await interaction.channel.set_permissions(
                role, view_channel=True, send_messages=True, read_message_history=True, attach_files=True
            )
            pings.append(role.mention)

    await refresh_ticket_message(interaction.channel, t["id"])
    await interaction.followup.send(
        f"🛡️ {' '.join(pings)} A middleman was requested by {interaction.user.mention}.",
        allowed_mentions=PINGS,
    )


# ------------------------------------------------------------- close flow
class CloseView(discord.ui.View):
    def __init__(self, user_id: int, can_complete: bool):
        super().__init__(timeout=60)
        self.user_id = user_id
        if not can_complete:
            self.remove_item(self.complete_close)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Deal completed & close", emoji="✅", style=discord.ButtonStyle.success)
    async def complete_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Logging the deal and closing...", view=None)
        ok, msg = await complete_deal(interaction.guild, interaction.channel, interaction.user)
        if not ok:
            return await interaction.followup.send(msg, ephemeral=True)
        await close_ticket(interaction.channel, interaction.user)

    @discord.ui.button(label="Close ticket", emoji="🔒", style=discord.ButtonStyle.danger)
    async def plain_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Closing ticket...", view=None)
        await close_ticket(interaction.channel, interaction.user)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled.", view=None)


async def open_close_prompt(user: discord.Member, channel_id: int, send):
    """`send` is an async function taking message kwargs (content, view)."""
    t = await get_ticket(channel_id)
    if not t or t["status"] != "open":
        return await send(content="This is not an open ticket.")

    is_staff = await member_has_kind(user, KIND_ROLE[t["kind"]])
    if not (is_staff or user.id == t["user_id"]):
        return await send(content="Only staff or the ticket owner can close this ticket.")

    can_complete = False
    if t["kind"] == "exchange" and is_staff and t["claimed_by"] and not t["completed"]:
        can_complete = t["claimed_by"] == user.id or await member_has_kind(user, "manager")

    if can_complete:
        text = "Was this deal **completed**? Completing it logs the deal and adds it to the stats."
    elif t["kind"] == "exchange" and is_staff and not t["claimed_by"] and not t["completed"]:
        text = "This ticket isn't claimed, so it can only be closed **without** a completed deal."
    else:
        text = "Close this ticket?"

    await send(content=text, view=CloseView(user.id, can_complete))


async def close_button(interaction: discord.Interaction):
    async def send(**kwargs):
        await interaction.response.send_message(ephemeral=True, **kwargs)
    await open_close_prompt(interaction.user, interaction.channel_id, send)


# ----------------------------------------------------------- complete a deal
async def complete_deal(guild: discord.Guild, channel: discord.TextChannel, staff: discord.Member):
    t = await get_ticket(channel.id)
    if not t or t["kind"] != "exchange":
        return False, "Only exchange tickets can be completed."
    if t["completed"]:
        return True, ""
    if not t["claimed_by"]:
        return False, "Claim the ticket first."
    if t["claimed_by"] != staff.id and not await member_has_kind(staff, "manager"):
        return False, "Only the staff member who claimed this ticket can complete it."

    tax_pct = await get_tax_percent(guild.id)
    tax = round((t["amount_usd"] or 0) * tax_pct / 100, 4)

    changed = await db.execute(
        "UPDATE tickets SET completed=1, completed_at=CURRENT_TIMESTAMP, tax_usd=? "
        "WHERE id=? AND completed=0",
        (tax, t["id"]),
    )
    if not changed:
        return True, ""

    cfg = EX_TYPES.get(t["ex_type"], {})
    embed = discord.Embed(title="Deal Logged", color=0x57F287)
    embed.add_field(name="Ticket", value=f"#{t['id']:04d}")
    embed.add_field(name="Client", value=f"<@{t['user_id']}>")
    embed.add_field(name="Handled by", value=f"<@{t['claimed_by']}>")
    embed.add_field(name="Category", value=cfg.get("category", "-"))
    embed.add_field(name="Amount", value=f"${t['amount_usd']:,.2f}")
    embed.add_field(name="Exchange", value=f"{t['send_asset']} -> {t['recv_asset']}")
    embed.add_field(name="Calculation", value=t["calc_text"] or "-", inline=False)
    embed.add_field(name="Tax recorded", value=f"${tax:,.4f} ({tax_pct:g}%)")

    log_id = await db.get_setting(guild.id, "deal_log_channel")
    if log_id:
        log_channel = guild.get_channel(int(log_id))
        if log_channel:
            await log_channel.send(embed=embed)
    return True, ""


# ------------------------------------------------------------------- close
async def close_ticket(channel: discord.TextChannel, closer: discord.abc.User):
    guild = channel.guild
    t = await get_ticket(channel.id)

    data = await build_transcript(channel)
    filename = f"transcript-{channel.name}.html"

    if t:
        await db.execute(
            "UPDATE tickets SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE id=?", (t["id"],)
        )

    log_id = await db.get_setting(guild.id, "transcript_channel")
    if log_id:
        log_channel = guild.get_channel(int(log_id))
        if log_channel:
            embed = discord.Embed(title="Ticket Closed", color=EMBED_COLOR)
            embed.add_field(name="Channel", value=channel.name)
            embed.add_field(name="Closed by", value=closer.mention)
            if t:
                embed.add_field(name="Type", value=t["kind"])
                embed.add_field(name="Opened by", value=f"<@{t['user_id']}>")
                embed.add_field(name="Claimed by", value=f"<@{t['claimed_by']}>" if t["claimed_by"] else "Nobody")
                embed.add_field(name="Deal completed", value="Yes" if t["completed"] else "No")
            await log_channel.send(embed=embed, file=discord.File(io.BytesIO(data), filename=filename))

    if t:
        member = guild.get_member(t["user_id"])
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
