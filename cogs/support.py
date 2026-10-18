import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import BRAND, EMBED_COLOR
from utils import tickets
from utils.checks import is_staff

class SupportModal(discord.ui.Modal, title="Support request"):
    issue = discord.ui.TextInput(
        label="Describe your issue", style=discord.TextStyle.paragraph, max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        existing = await db.fetchone(
            "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? "
            "AND kind='support' AND status='open'",
            (interaction.guild_id, interaction.user.id),
        )
        if existing:
            return await interaction.followup.send(
                f"You already have an open support ticket: <#{existing['channel_id']}>", ephemeral=True
            )

        ticket_id = await db.insert(
            "INSERT INTO tickets (guild_id, channel_id, user_id, kind) VALUES (?, 0, ?, 'support')",
            (interaction.guild_id, interaction.user.id),
        )
        try:
            channel = await tickets.create_ticket_channel(
                interaction.guild, interaction.user, name=f"support-{ticket_id:04d}"
            )
        except discord.HTTPException:
            await db.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
            return await interaction.followup.send("Could not create the ticket.", ephemeral=True)

        await db.execute("UPDATE tickets SET channel_id=? WHERE id=?", (channel.id, ticket_id))

        embed = discord.Embed(title="Support Ticket", description=self.issue.value, color=EMBED_COLOR)
        embed.add_field(name="Opened by", value=interaction.user.mention)

        role_id = await db.get_setting(interaction.guild_id, "staff_role")
        ping = f"<@&{role_id}> " if role_id else ""
        await channel.send(
            f"{ping}{interaction.user.mention}", embed=embed, view=SupportTicketView(),
            allowed_mentions=discord.AllowedMentions(roles=True, users=True),
        )
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class SupportPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Support Ticket", emoji="🎫", style=discord.ButtonStyle.primary,
                       custom_id="support:open")
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SupportModal())

class SupportTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", emoji="✅", style=discord.ButtonStyle.success,
                       custom_id="support:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await tickets.claim_ticket(interaction):
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.channel.send(f"✅ Claimed by {interaction.user.mention}.")

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger,
                       custom_id="support:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.prompt_close(interaction)

class ApplicationModal(discord.ui.Modal, title="Staff application"):
    age = discord.ui.TextInput(label="Age", max_length=3)
    experience = discord.ui.TextInput(
        label="Exchange / moderation experience", style=discord.TextStyle.paragraph, max_length=800
    )
    why = discord.ui.TextInput(
        label="Why should we pick you?", style=discord.TextStyle.paragraph, max_length=800
    )
    availability = discord.ui.TextInput(label="Timezone and daily availability", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        channel_id = await db.get_setting(interaction.guild_id, "applications_channel")
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
        if not channel:
            return await interaction.response.send_message(
                "Applications are not configured yet. Please contact an admin.", ephemeral=True
            )

        embed = discord.Embed(title="New Staff Application", color=EMBED_COLOR)
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)
        embed.add_field(name="Age", value=self.age.value)
        embed.add_field(name="Availability", value=self.availability.value)
        embed.add_field(name="Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Why them", value=self.why.value, inline=False)
        embed.set_footer(text=f"Applicant ID: {interaction.user.id}")

        await channel.send(embed=embed, view=ApplicationReviewView())
        await interaction.response.send_message("✅ Application submitted. Good luck!", ephemeral=True)

class ApplyPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply for Staff", emoji="📝", style=discord.ButtonStyle.primary,
                       custom_id="apply:open")
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal())

class ApplicationReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _decide(self, interaction: discord.Interaction, accepted: bool):
        if not await is_staff(interaction):
            return await interaction.response.send_message("Staff only.", ephemeral=True)

        embed = interaction.message.embeds[0]
        applicant_id = int(embed.footer.text.split(":")[1].strip())

        embed.color = discord.Color.green() if accepted else discord.Color.red()
        embed.add_field(
            name="Decision",
            value=f"{'Accepted' if accepted else 'Denied'} by {interaction.user.mention}",
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=None)

        try:
            user = await interaction.client.fetch_user(applicant_id)
            msg = ("🎉 Your staff application was **accepted**. A manager will contact you."
                   if accepted else "Your staff application was not accepted this time.")
            await user.send(f"{BRAND}: {msg}")
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, custom_id="apply:accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._decide(interaction, True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="apply:deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._decide(interaction, True)

class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        for view in (SupportPanelView(), SupportTicketView(), ApplyPanelView(), ApplicationReviewView()):
            self.bot.add_view(view)

    @app_commands.command(name="support_panel", description="Post the support ticket panel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def support_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{BRAND} - Support",
            description="Need help with a deal or have a question? Open a ticket below.",
            color=EMBED_COLOR,
        )
        await interaction.channel.send(embed=embed, view=SupportPanelView())
        await interaction.response.send_message("Panel posted.", ephemeral=True)

    @app_commands.command(name="apply_panel", description="Post the staff application panel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def apply_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{BRAND} - Staff Applications",
            description="Want to join the team? Press the button and fill in the form.",
            color=EMBED_COLOR,
        )
        await interaction.channel.send(embed=embed, view=ApplyPanelView())
        await interaction.response.send_message("Panel posted.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
