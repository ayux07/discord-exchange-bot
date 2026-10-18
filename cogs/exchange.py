import math
import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import BRAND, EMBED_COLOR, EX_TYPES, INR_METHODS, CRYPTOS
from utils import tickets
from utils.calc import calculate
from utils.checks import is_staff

MENTIONS = discord.AllowedMentions(roles=True, users=True, everyone=False)

def panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title=BRAND,
        description="**SECURE EXCHANGE SERVICE**\nLive staff, private tickets, fast handling.",
        color=EMBED_COLOR,
    )
    for cfg in EX_TYPES.values():
        embed.add_field(
            name=cfg["label"],
            value=f"> Fee: **{cfg['fee']}%**\n> Min: **{cfg['min']} {cfg['unit']}**",
            inline=False,
        )
    embed.set_footer(text="Select an exchange type below to open a ticket.")
    return embed

class ExchangeTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=cfg["label"], value=key,
                description=f"Fee: {cfg['fee']}% | Min: {cfg['min']} {cfg['unit']}",
            )
            for key, cfg in EX_TYPES.items()
        ]
        super().__init__(
            placeholder="Choose an exchange type",
            options=options,
            custom_id="exchange:type",
        )

    async def callback(self, interaction: discord.Interaction):
        ex_type = self.values[0]

        existing = await db.fetchone(
            "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? "
            "AND kind='exchange' AND status='open'",
            (interaction.guild_id, interaction.user.id),
        )
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: <#{existing['channel_id']}>", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Pick your options, then press **Continue**.",
                view=OptionsView(ex_type), ephemeral=True,
            )

        try:
            await interaction.message.edit(view=ExchangePanelView())
        except discord.HTTPException:
            pass

class ExchangePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ExchangeTypeSelect())

class ChoiceSelect(discord.ui.Select):
    def __init__(self, placeholder: str, choices: list[str], attr: str, row: int):
        super().__init__(
            placeholder=placeholder,
            options=[discord.SelectOption(label=c) for c in choices],
            row=row,
        )
        self.attr = attr

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        setattr(self.view, self.attr, chosen)
        for opt in self.options:
            opt.default = opt.label == chosen
        await interaction.response.edit_message(view=self.view)

class OptionsView(discord.ui.View):
    def __init__(self, ex_type: str):
        super().__init__(timeout=300)
        self.ex_type = ex_type
        self.method = None
        self.crypto = None

        if ex_type == "crypto_to_crypto":
            self.add_item(ChoiceSelect("Crypto you are SENDING", CRYPTOS, "method", row=0))
            self.add_item(ChoiceSelect("Crypto you want to RECEIVE", CRYPTOS, "crypto", row=1))
        elif ex_type == "inr_to_crypto":
            self.add_item(ChoiceSelect("INR method you will PAY with", INR_METHODS, "method", row=0))
            self.add_item(ChoiceSelect("Crypto you want to RECEIVE", CRYPTOS, "crypto", row=1))
        else:
            self.add_item(ChoiceSelect("INR method you want to RECEIVE on", INR_METHODS, "method", row=0))
            self.add_item(ChoiceSelect("Crypto you are SENDING", CRYPTOS, "crypto", row=1))

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success, row=2)
    async def go(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.method or not self.crypto:
            return await interaction.response.send_message(
                "Please choose both options first.", ephemeral=True
            )
        if self.ex_type == "crypto_to_crypto" and self.method == self.crypto:
            return await interaction.response.send_message(
                "Sending and receiving coins must be different.", ephemeral=True
            )
        await interaction.response.send_modal(
            DetailsModal(self.ex_type, self.method, self.crypto)
        )

class DetailsModal(discord.ui.Modal):
    def __init__(self, ex_type: str, method: str, crypto: str):
        super().__init__(title="Exchange details")
        self.ex_type, self.method, self.crypto = ex_type, method, crypto
        cfg = EX_TYPES[ex_type]

        self.amount = discord.ui.TextInput(
            label=f"Exchange amount ({cfg['unit']})", placeholder="e.g. 1000", max_length=12
        )
        payout_label = {
            "inr_to_crypto": "Your wallet address (to receive crypto)",
            "crypto_to_inr": "Your UPI ID / bank details (to receive INR)",
            "crypto_to_crypto": "Your wallet address (to receive crypto)",
        }[ex_type]
        self.payout = discord.ui.TextInput(
            label=payout_label, style=discord.TextStyle.paragraph, max_length=300
        )
        self.add_item(self.amount)
        self.add_item(self.payout)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        cfg = EX_TYPES[self.ex_type]

        try:
            amount = float(self.amount.value.replace(",", "").strip())
        except ValueError:
            return await interaction.followup.send("Amount must be a number.", ephemeral=True)
        if not math.isfinite(amount) or amount <= 0:
            return await interaction.followup.send("Enter a valid positive amount.", ephemeral=True)
        if amount < cfg["min"]:
            return await interaction.followup.send(
                f"Minimum for this exchange is {cfg['min']} {cfg['unit']}.", ephemeral=True
            )

        try:
            calc = await calculate(self.ex_type, amount, self.method, self.crypto, cfg["fee"])
        except Exception:
            return await interaction.followup.send(
                "Could not fetch live rates right now. Please try again in a minute.", ephemeral=True
            )

        payout = self.payout.value.strip()
        ticket_id = await db.insert(
            "INSERT INTO tickets (guild_id, channel_id, user_id, kind, ex_type, method, crypto, "
            "amount, fee, receive_amount, rate, payout_details, volume_inr) "
            "VALUES (?, 0, ?, 'exchange', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (interaction.guild_id, interaction.user.id, self.ex_type, self.method, self.crypto,
             amount, calc["fee"], calc["receive"], calc["rate"], payout, calc["volume_inr"]),
        )

        try:
            channel = await tickets.create_ticket_channel(
                interaction.guild, interaction.user,
                name=f"{cfg['slug']}-{ticket_id:04d}",
                topic=f"Exchange ticket #{ticket_id} for {interaction.user}",
            )
        except discord.HTTPException:
            await db.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
            return await interaction.followup.send(
                "I could not create the ticket channel. Ask an admin to check my permissions.",
                ephemeral=True,
            )

        await db.execute("UPDATE tickets SET channel_id=? WHERE id=?", (channel.id, ticket_id))

        embed = discord.Embed(title=f"{BRAND} - Transaction Details", color=EMBED_COLOR)
        embed.add_field(name="Ticket", value=f"#{ticket_id:04d}")
        embed.add_field(name="Customer", value=interaction.user.mention)
        embed.add_field(name="Type", value=cfg["label"])
        embed.add_field(name="You send", value=calc["send_text"], inline=False)
        embed.add_field(name="Fee", value=calc["fee_text"])
        embed.add_field(name="You receive", value=calc["receive_text"])
        embed.add_field(name="Rate used", value=calc["rate_text"], inline=False)
        embed.add_field(name="Payout details", value=f"```{payout.replace('`', chr(39))}```", inline=False)
        embed.set_footer(text="Rates are estimates. Staff will confirm the final amount before you pay.")

        staff_role_id = await db.get_setting(interaction.guild_id, "staff_role")
        ping = f"<@&{staff_role_id}> " if staff_role_id else ""
        await channel.send(
            content=f"{ping}{interaction.user.mention}",
            embed=embed, view=ExchangeTicketView(), allowed_mentions=MENTIONS,
        )
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class ExchangeTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", emoji="✅", style=discord.ButtonStyle.success,
                       custom_id="exchange:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await tickets.claim_ticket(interaction):
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.channel.send(f"✅ Ticket claimed by {interaction.user.mention}.")

    @discord.ui.button(label="Complete Deal", emoji="💰", style=discord.ButtonStyle.primary,
                       custom_id="exchange:complete")
    async def complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_staff(interaction):
            return await interaction.response.send_message("Staff only.", ephemeral=True)

        ticket = await tickets.get_ticket(interaction.channel_id)
        if not ticket:
            return await interaction.response.send_message("Ticket not found.", ephemeral=True)

        is_admin = interaction.user.guild_permissions.administrator
        if ticket["claimed_by"] != interaction.user.id and not is_admin:
            return await interaction.response.send_message(
                "Only the staff member who claimed this ticket can complete it.", ephemeral=True
            )

        changed = await db.execute(
            "UPDATE tickets SET completed=1 WHERE channel_id=? AND completed=0",
            (interaction.channel_id,),
        )
        if not changed:
            return await interaction.response.send_message("Already marked complete.", ephemeral=True)

        cfg = EX_TYPES[ticket["ex_type"]]
        log = discord.Embed(title="Deal Logged", color=0x57F287)
        log.add_field(name="Ticket", value=f"#{ticket['id']:04d}")
        log.add_field(name="Customer", value=f"<@{ticket['user_id']}>")
        log.add_field(name="Handled by", value=interaction.user.mention)
        log.add_field(name="Type", value=cfg["label"])
        log.add_field(name="Amount", value=f"{ticket['amount']:,.2f} {cfg['unit']}")
        log.add_field(name="Fee", value=f"{ticket['fee']:,.2f} {cfg['unit']}")
        log.add_field(name="Method / Coin", value=f"{ticket['method']} / {ticket['crypto']}")

        log_id = await db.get_setting(interaction.guild_id, "deal_log_channel")
        if log_id:
            channel = interaction.guild.get_channel(int(log_id))
            if channel:
                await channel.send(embed=log)

        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send("💰 Deal marked as **completed**. You can now close the ticket.")

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger,
                       custom_id="exchange:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.prompt_close(interaction)

class ExchangeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(ExchangePanelView())
        self.bot.add_view(ExchangeTicketView())

    @app_commands.command(name="exchange_panel", description="Post the exchange panel in this channel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def exchange_panel(self, interaction: discord.Interaction):
        await interaction.channel.send(embed=panel_embed(), view=ExchangePanelView())
        await interaction.response.send_message("Panel posted.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ExchangeCog(bot))
