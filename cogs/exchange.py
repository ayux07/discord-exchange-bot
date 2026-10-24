# cogs/exchange.py
import math
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands

import database as db
from config import (BRAND, EMBED_COLOR, EX_TYPES, INR_METHODS, CRYPTOS, LOGO_PATH,
                    PANEL_AMOUNT_TEXT, MIN_USD, TIMEZONE)
from utils import tickets
from utils.calc import calculate, get_rate, get_c2c_fee
from utils.checks import require, SafeModal
from utils.ticket_views import ExchangeTicketView


def enabled_types() -> dict:
    return {k: v for k, v in EX_TYPES.items() if v["enabled"]}


# ============================================================== PANEL EMBED
async def build_panel_embed(guild_id: int) -> discord.Embed:
    lines = ["# SECURE EXCHANGE SERVICE", "", "Live staff • Private tickets • Fast handling", ""]
    for key, cfg in enabled_types().items():
        if key == "crypto_to_crypto":
            info = f"{PANEL_AMOUNT_TEXT} • {await get_c2c_fee(guild_id):g}% fee"
        else:
            info = f"{PANEL_AMOUNT_TEXT} • {await get_rate(guild_id, key):g} / $"
        lines += [f"**{cfg['panel_title']}**", info, ""]
    lines.append("Select an exchange type below")

    embed = discord.Embed(description="\n".join(lines), color=EMBED_COLOR)
    embed.set_author(name=BRAND)                              # small brand line at the top
    if os.path.exists(LOGO_PATH):
        embed.set_thumbnail(url="attachment://logo.png")      # logo on the right
    return embed


# ======================================================= STEP 1: DROPDOWN
class ExchangeTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cfg["label"], value=key, description=f"{cfg['category']} exchange")
            for key, cfg in enabled_types().items()
        ]
        super().__init__(placeholder="Choose an exchange type", options=options,
                         custom_id="exchange:type")

    async def callback(self, interaction: discord.Interaction):
        ex_type = self.values[0]

        existing = await tickets.existing_open(interaction.guild_id, interaction.user.id, "exchange")
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: <#{existing['channel_id']}>", ephemeral=True
            )
        else:
            view = OptionsView(ex_type)
            await interaction.response.send_message(
                "Pick your options, then press **Continue**.", view=view, ephemeral=True
            )
            view.origin = interaction          # remembered so we can delete this message later

        # reset the dropdown so the same option can be picked again
        try:
            await interaction.message.edit(view=ExchangePanelView())
        except discord.HTTPException:
            pass


class ExchangePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ExchangeTypeSelect())


# ================================================ STEP 2: THE TWO DROPDOWNS
class ChoiceSelect(discord.ui.Select):
    def __init__(self, placeholder: str, choices: list, attr: str, row: int):
        super().__init__(
            placeholder=placeholder,
            options=[discord.SelectOption(label=label, value=value) for label, value in choices],
            row=row,
        )
        self.attr = attr

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        setattr(self.view, self.attr, chosen)
        for opt in self.options:                       # show the choice inside the dropdown
            opt.default = opt.value == chosen
        await interaction.response.edit_message(view=self.view)


class OptionsView(discord.ui.View):
    """First dropdown = what you SEND, second = what you RECEIVE."""
    def __init__(self, ex_type: str):
        super().__init__(timeout=300)
        self.ex_type = ex_type
        self.send = None
        self.recv = None
        self.origin: discord.Interaction | None = None

        inr = list(INR_METHODS.items())                 # (label, code)
        crypto = [(c, c) for c in CRYPTOS]

        if ex_type == "inr_to_crypto":
            first, second = inr, crypto
        elif ex_type == "crypto_to_inr":
            first, second = crypto, inr
        else:
            first, second = crypto, crypto

        self.add_item(ChoiceSelect("What are you SENDING?", first, "send", row=0))
        self.add_item(ChoiceSelect("What do you want to RECEIVE?", second, "recv", row=1))

    async def dismiss(self):
        """Delete the picker message (called after the ticket is created or on timeout)."""
        self.stop()
        if self.origin:
            try:
                await self.origin.delete_original_response()
            except discord.HTTPException:
                pass

    async def on_timeout(self):
        await self.dismiss()

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success, row=2)
    async def go(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.send or not self.recv:
            return await interaction.response.send_message("Please choose both options first.", ephemeral=True)
        if self.send == self.recv:
            return await interaction.response.send_message("Sending and receiving can't be the same.", ephemeral=True)
        await interaction.response.send_modal(DetailsModal(self))


# =========================================================== STEP 3: FORM
class DetailsModal(SafeModal):
    def __init__(self, picker: OptionsView):
        super().__init__(title="Exchange details")
        self.picker = picker
        self.amount = discord.ui.TextInput(label="Exchange amount (USD)", placeholder="e.g. 5", max_length=10)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        p = self.picker
        cfg = EX_TYPES[p.ex_type]

        try:
            amount = float(self.amount.value.replace(",", "").replace("$", "").strip())
        except ValueError:
            return await interaction.followup.send("Amount must be a number.", ephemeral=True)
        if not math.isfinite(amount) or amount <= 0:
            return await interaction.followup.send("Enter a valid positive amount.", ephemeral=True)
        if amount < MIN_USD:
            return await interaction.followup.send(f"Minimum amount is ${MIN_USD:g}.", ephemeral=True)

        existing = await tickets.existing_open(interaction.guild_id, interaction.user.id, "exchange")
        if existing:
            return await interaction.followup.send(
                f"You already have an open ticket: <#{existing['channel_id']}>", ephemeral=True
            )

        calc = await calculate(interaction.guild_id, p.ex_type, amount, p.send, p.recv)

        try:
            ticket_id, channel = await tickets.new_ticket(
                interaction.guild, interaction.user, "exchange", cfg["slug"],
                {
                    "ex_type": p.ex_type, "send_asset": p.send, "recv_asset": p.recv,
                    "amount_usd": amount, "inr_amount": calc["inr_amount"], "rate": calc["rate"],
                    "fee_usd": calc["fee_usd"], "calc_text": calc["calc_text"],
                },
            )
        except discord.HTTPException:
            return await interaction.followup.send(
                "I couldn't create the ticket channel. Ask an admin to check my permissions and the ticket category.",
                ephemeral=True,
            )

        pings = await tickets.staff_pings(interaction.guild, "exchange")
        message = await channel.send(
            content=f"{pings} {interaction.user.mention}".strip(),
            embed=ticket_embed(interaction.user, cfg, amount, p.send, p.recv, calc),
            view=ExchangeTicketView(),
            allowed_mentions=tickets.PINGS,
        )
        await db.execute("UPDATE tickets SET message_id=? WHERE id=?", (message.id, ticket_id))

        await p.dismiss()                                   # picker message deletes itself
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


# ===================================================== THE TICKET EMBED
def ticket_embed(member: discord.Member, cfg: dict, amount: float, send: str, recv: str, calc: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"{BRAND} — Transaction Details",
        description="Your ticket will shortly be reviewed by an exchanger.\nPlease wait patiently.",
        color=EMBED_COLOR,
    )
    embed.add_field(name="Client", value=f"{member.mention}\n`{member.id}`", inline=False)
    embed.add_field(name="Category", value=f"`{cfg['category']}`", inline=False)
    embed.add_field(name="Amount", value=f"`${amount:,.2f}`", inline=False)
    embed.add_field(name="Exchange", value=f"`{send} -> {recv}`", inline=False)
    embed.add_field(name="You Sending", value=f"`{send}`", inline=False)
    embed.add_field(name="You Receiving", value=f"`{recv}`", inline=False)
    embed.add_field(name="Auto Calculation", value=f"`{calc['calc_text']}`", inline=False)
    now = datetime.now(ZoneInfo(TIMEZONE))
    embed.set_footer(text=f"Requested by {member.name} • Confirmed | {now:%d/%m/%Y %H:%M}")
    return embed


# ================================================================== COG
class ExchangeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(ExchangePanelView())
        self.bot.add_view(ExchangeTicketView())

    @commands.hybrid_command(name="exchangepanel", description="Post the exchange panel in this channel")
    @require("manager")
    @commands.guild_only()
    async def exchangepanel(self, ctx: commands.Context):
        file = discord.File(LOGO_PATH, filename="logo.png") if os.path.exists(LOGO_PATH) else None
        await ctx.channel.send(embed=await build_panel_embed(ctx.guild.id), view=ExchangePanelView(), file=file)
        if ctx.interaction:
            await ctx.send("Panel posted.", ephemeral=True)
        else:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ExchangeCog(bot))
