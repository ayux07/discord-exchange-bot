# utils/ticket_views.py
import discord
import database as db
from utils import tickets
from utils.checks import member_has_kind


class ExchangeTicketView(discord.ui.View):
    """Claim (green) | Req MM (grey) | Close (red)"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="exchange:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.claim_button(interaction)

    @discord.ui.button(label="Req MM", style=discord.ButtonStyle.secondary, custom_id="exchange:mm")
    async def mm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.request_mm(interaction)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="exchange:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.close_button(interaction)


class SupportTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="support:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.claim_button(interaction)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="support:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.close_button(interaction)


async def _decide(interaction: discord.Interaction, accepted: bool):
    t = await tickets.get_ticket(interaction.channel_id)
    if not t or t["status"] != "open":
        return await interaction.response.send_message("This is not an open application.", ephemeral=True)
    if not await member_has_kind(interaction.user, "application"):
        return await interaction.response.send_message(
            "Only the Owner / Founder roles can decide applications.", ephemeral=True
        )

    decision = "accepted" if accepted else "denied"
    changed = await db.execute(
        "UPDATE tickets SET decision=? WHERE id=? AND decision IS NULL", (decision, t["id"])
    )
    if not changed:
        return await interaction.response.send_message("A decision was already made.", ephemeral=True)

    await interaction.response.defer()
    await tickets.refresh_ticket_message(interaction.channel, t["id"])

    embed = discord.Embed(
        title=f"Application {decision.title()}",
        description=f"Decision by {interaction.user.mention}.",
        color=0x57F287 if accepted else 0xED4245,
    )
    await interaction.followup.send(embed=embed)

    try:
        user = interaction.guild.get_member(t["user_id"]) or await interaction.client.fetch_user(t["user_id"])
        await user.send(
            f"Your staff application in **{interaction.guild.name}** was **{decision}**."
            + (" A manager will contact you soon." if accepted else "")
        )
    except discord.HTTPException:
        pass


class ApplyTicketView(discord.ui.View):
    """Only Owner/Founder (role kind 'application') can use these."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="apply:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.claim_button(interaction)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.primary, custom_id="apply:accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _decide(interaction, True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.secondary, custom_id="apply:deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _decide(interaction, False)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="apply:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.close_button(interaction)


VIEW_FOR_KIND = {
    "exchange": ExchangeTicketView,
    "support": SupportTicketView,
    "apply": ApplyTicketView,
}
