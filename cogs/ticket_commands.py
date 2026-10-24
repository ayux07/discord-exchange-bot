# cogs/ticket_commands.py
import io
import discord
from discord.ext import commands

import database as db
from config import EMBED_COLOR, EX_TYPES, VOUCH_FORMAT
from utils import tickets
from utils.checks import member_has_kind
from utils.transcript import build_transcript


class TicketCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """If someone deletes a ticket channel by hand, mark the ticket closed so the user can open a new one."""
        await db.execute(
            "UPDATE tickets SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE channel_id=? AND status='open'",
            (channel.id,),
        )

    # ------------------------------------------------------------ claim
    @commands.hybrid_command(name="claim", description="Claim this ticket")
    @commands.guild_only()
    async def claim(self, ctx: commands.Context):
        await ctx.defer()
        ok, msg = await tickets.do_claim(ctx.author, ctx.channel)
        await ctx.send(f"✅ Ticket claimed by {ctx.author.mention}." if ok else msg, ephemeral=not ok)

    @commands.hybrid_command(name="uc", aliases=["unclaim"], description="Unclaim this ticket")
    @commands.guild_only()
    async def unclaim(self, ctx: commands.Context):
        await ctx.defer()
        ok, msg = await tickets.do_unclaim(ctx.author, ctx.channel)
        await ctx.send("↩️ Ticket unclaimed." if ok else msg, ephemeral=not ok)

    # ------------------------------------------------------------ close
    @commands.hybrid_command(name="close", description="Close this ticket")
    @commands.guild_only()
    async def close(self, ctx: commands.Context):
        async def send(**kwargs):
            await ctx.send(ephemeral=True, **kwargs)
        await tickets.open_close_prompt(ctx.author, ctx.channel.id, send)

    # ------------------------------------------------------- transcript
    @commands.hybrid_command(name="transcript", description="Generate a transcript of this ticket")
    @commands.guild_only()
    async def transcript(self, ctx: commands.Context):
        t = await tickets.get_ticket(ctx.channel.id)
        if not t:
            return await ctx.send("This is not a ticket channel.", ephemeral=True)
        if not await member_has_kind(ctx.author, tickets.KIND_ROLE[t["kind"]]):
            return await ctx.send("Only staff for this ticket type can do that.", ephemeral=True)
        await ctx.defer()
        data = await build_transcript(ctx.channel)
        await ctx.send("📄 Transcript:", file=discord.File(io.BytesIO(data), filename=f"transcript-{ctx.channel.name}.html"))

    # ------------------------------------------------------ vouch format
    @commands.hybrid_command(name="v", description="Generate a vouch message for this deal")
    @commands.guild_only()
    async def vouch_format(self, ctx: commands.Context):
        t = await tickets.get_ticket(ctx.channel.id)
        if not t or t["kind"] != "exchange":
            return await ctx.send("Use this inside an exchange ticket.", ephemeral=True)
        is_staff = await member_has_kind(ctx.author, "exchanger")
        if not (is_staff or ctx.author.id == t["user_id"]):
            return await ctx.send("Only the client or staff can use this.", ephemeral=True)
        if not t["claimed_by"]:
            return await ctx.send("Nobody has claimed this ticket yet.", ephemeral=True)

        staff = ctx.guild.get_member(t["claimed_by"])
        text = VOUCH_FORMAT.format(
            staff=staff.name if staff else "staff",
            category=EX_TYPES[t["ex_type"]]["category"],
            amount=t["amount_usd"],
            exchange=f"{t['send_asset']} -> {t['recv_asset']}",
        )
        embed = discord.Embed(title="Vouch format", description=f"Copy and post this in the vouch channel:\n```{text}```",
                              color=EMBED_COLOR)
        await ctx.send(embed=embed)

    # ---------------------------------------------------- third party
    @commands.hybrid_command(name="3p", description="Add or remove a third party in this ticket")
    @commands.guild_only()
    async def third_party(self, ctx: commands.Context, user: discord.Member):
        t = await tickets.get_ticket(ctx.channel.id)
        if not t or t["status"] != "open":
            return await ctx.send("This is not an open ticket.", ephemeral=True)
        if not await member_has_kind(ctx.author, tickets.KIND_ROLE[t["kind"]]):
            return await ctx.send("Only staff for this ticket type can do that.", ephemeral=True)
        if user.bot or user.id == t["user_id"]:
            return await ctx.send("Pick a different user.", ephemeral=True)

        if ctx.channel.overwrites_for(user).view_channel:          # already added → remove
            await ctx.channel.set_permissions(user, overwrite=None)
            await ctx.send(f"➖ {user.mention} was removed from this ticket.")
        else:
            await ctx.channel.set_permissions(
                user, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
            await ctx.send(f"➕ {user.mention} was added to this ticket as a third party.")


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCommands(bot))
