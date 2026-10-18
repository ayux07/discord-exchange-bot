from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
import database as db

class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Configure the exchange bot for this server")
    @app_commands.describe(
        staff_role="Role that can claim and close tickets",
        ticket_category="Category where ticket channels are created",
        deal_log_channel="Channel for 'Deal Logged' messages",
        transcript_channel="Channel for ticket transcripts",
        applications_channel="Channel where staff applications arrive",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup(
        self,
        interaction: discord.Interaction,
        staff_role: discord.Role,
        ticket_category: discord.CategoryChannel,
        deal_log_channel: discord.TextChannel,
        transcript_channel: discord.TextChannel,
        applications_channel: Optional[discord.TextChannel] = None,
    ):
        gid = interaction.guild_id
        await db.set_setting(gid, "staff_role", staff_role.id)
        await db.set_setting(gid, "ticket_category", ticket_category.id)
        await db.set_setting(gid, "deal_log_channel", deal_log_channel.id)
        await db.set_setting(gid, "transcript_channel", transcript_channel.id)
        if applications_channel:
            await db.set_setting(gid, "applications_channel", applications_channel.id)

        await interaction.response.send_message(
            f"✅ Saved.\n"
            f"Staff role: {staff_role.mention}\n"
            f"Ticket category: {ticket_category.mention}\n"
            f"Deal logs: {deal_log_channel.mention}\n"
            f"Transcripts: {transcript_channel.mention}\n"
            f"Applications: {applications_channel.mention if applications_channel else 'not set'}",
            ephemeral=True,
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
