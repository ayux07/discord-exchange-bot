# cogs/support.py
import os
import discord
from discord.ext import commands

import database as db
from config import BRAND, EMBED_COLOR, LOGO_PATH
from utils import tickets
from utils.checks import require, SafeModal
from utils.ticket_views import SupportTicketView, ApplyTicketView


# ============================================================ SUPPORT
class SupportModal(SafeModal):
    def __init__(self):
        super().__init__(title="Support request")
        self.issue = discord.ui.TextInput(label="Describe your issue", style=discord.TextStyle.paragraph,
                                          max_length=1000)
        self.add_item(self.issue)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        existing = await tickets.existing_open(interaction.guild_id, interaction.user.id, "support")
        if existing:
            return await interaction.followup.send(
                f"You already have an open support ticket: <#{existing['channel_id']}>", ephemeral=True)

        try:
            ticket_id, channel = await tickets.new_ticket(
                interaction.guild, interaction.user, "support", "support", {})
        except discord.HTTPException:
            return await interaction.followup.send("I couldn't create the ticket.", ephemeral=True)

        embed = discord.Embed(
            title=f"{BRAND} — Support Ticket",
            description="A support member will be with you shortly.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Client", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=False)
        embed.add_field(name="Issue", value=self.issue.value, inline=False)

        pings = await tickets.staff_pings(interaction.guild, "support")
        message = await channel.send(
            content=f"{pings} {interaction.user.mention}".strip(),
            embed=embed, view=SupportTicketView(), allowed_mentions=tickets.PINGS,
        )
        await db.execute("UPDATE tickets SET message_id=? WHERE id=?", (message.id, ticket_id))
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


class SupportPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Support Ticket", emoji="🎫", style=discord.ButtonStyle.primary,
                       custom_id="support:open")
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SupportModal())


# ========================================================== APPLICATIONS
class ApplyModal(SafeModal):
    def __init__(self):
        super().__init__(title="Staff application")
        self.age = discord.ui.TextInput(label="Age", max_length=3)
        self.experience = discord.ui.TextInput(label="Exchange / moderation experience",
                                               style=discord.TextStyle.paragraph, max_length=800)
        self.why = discord.ui.TextInput(label="Why should we pick you?",
                                        style=discord.TextStyle.paragraph, max_length=800)
        self.availability = discord.ui.TextInput(label="Timezone and daily availability", max_length=100)
        for item in (self.age, self.experience, self.why, self.availability):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        existing = await tickets.existing_open(interaction.guild_id, interaction.user.id, "apply")
        if existing:
            return await interaction.followup.send(
                f"You already have an open application: <#{existing['channel_id']}>", ephemeral=True)

        try:
            ticket_id, channel = await tickets.new_ticket(
                interaction.guild, interaction.user, "apply", "apply", {})
        except discord.HTTPException:
            return await interaction.followup.send("I couldn't create the application ticket.", ephemeral=True)

        embed = discord.Embed(title=f"{BRAND} — Staff Application", color=EMBED_COLOR)
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Applicant", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=False)
        embed.add_field(name="Age", value=f"`{self.age.value}`")
        embed.add_field(name="Availability", value=f"`{self.availability.value}`")
        embed.add_field(name="Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Why them", value=self.why.value, inline=False)

        pings = await tickets.staff_pings(interaction.guild, "apply")      # Owner / Founder only
        message = await channel.send(
            content=f"{pings} {interaction.user.mention}".strip(),
            embed=embed, view=ApplyTicketView(), allowed_mentions=tickets.PINGS,
        )
        await db.execute("UPDATE tickets SET message_id=? WHERE id=?", (message.id, ticket_id))
        await interaction.followup.send(f"✅ Application submitted: {channel.mention}", ephemeral=True)


class ApplyPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply for Staff", emoji="📝", style=discord.ButtonStyle.primary,
                       custom_id="apply:open")
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplyModal())


# ================================================================== COG
class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        for view in (SupportPanelView(), SupportTicketView(), ApplyPanelView(), ApplyTicketView()):
            self.bot.add_view(view)

    async def _post(self, ctx: commands.Context, embed: discord.Embed, view: discord.ui.View):
        file = discord.File(LOGO_PATH, filename="logo.png") if os.path.exists(LOGO_PATH) else None
        if file:
            embed.set_thumbnail(url="attachment://logo.png")
        await ctx.channel.send(embed=embed, view=view, file=file)
        if ctx.interaction:
            await ctx.send("Panel posted.", ephemeral=True)
        else:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass

    @commands.hybrid_command(name="supportpanel", description="Post the support ticket panel")
    @require("manager")
    @commands.guild_only()
    async def supportpanel(self, ctx: commands.Context):
        embed = discord.Embed(
            description="# SUPPORT\n\nNeed help with a deal or have a question?\nOpen a ticket and our team will assist you.",
            color=EMBED_COLOR)
        embed.set_author(name=BRAND)
        await self._post(ctx, embed, SupportPanelView())

    @commands.hybrid_command(name="applypanel", description="Post the staff application panel")
    @require("manager")
    @commands.guild_only()
    async def applypanel(self, ctx: commands.Context):
        embed = discord.Embed(
            description="# STAFF APPLICATIONS\n\nWant to join the team?\nPress the button and fill in the form.",
            color=EMBED_COLOR)
        embed.set_author(name=BRAND)
        await self._post(ctx, embed, ApplyPanelView())


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
