# cogs/stats.py
import math
from datetime import datetime, timezone
from typing import Literal, Optional

import discord
from discord.ext import commands

import database as db
from config import BRAND, EMBED_COLOR
from utils.checks import require
from utils.confirm import ConfirmView

MEDALS = ["🥇", "🥈", "🥉"]
EPOCH_DEFAULT = "1970-01-01 00:00:00"


async def get_epoch(gid: int) -> str:
    return await db.get_setting(gid, "lb_epoch") or EPOCH_DEFAULT


def month_start() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-01 00:00:00")


async def board_data(gid: int, board: str, since: str, include_manual: bool):
    """Returns a ranked list: [(user_id, [deals, volume_usd]), ...]"""
    col = "user_id" if board == "users" else "claimed_by"       # hardcoded choice, never user input
    rows = await db.fetchall(
        f"SELECT {col} AS uid, COUNT(*) AS deals, COALESCE(SUM(amount_usd), 0) AS vol "
        f"FROM tickets WHERE guild_id=? AND kind='exchange' AND completed=1 AND completed_at >= ? "
        f"AND {col} IS NOT NULL GROUP BY {col}",
        (gid, since),
    )
    data = {r["uid"]: [r["deals"], r["vol"]] for r in rows}

    if include_manual and board == "users":
        for m in await db.fetchall("SELECT user_id, deals, volume_usd FROM manual_stats WHERE guild_id=?", (gid,)):
            entry = data.setdefault(m["user_id"], [0, 0.0])
            entry[0] += m["deals"]
            entry[1] += m["volume_usd"]

    ranked = [(uid, v) for uid, v in data.items() if v[0] > 0 or v[1] > 0]
    ranked.sort(key=lambda kv: kv[1][1], reverse=True)
    return ranked


def render_board(title: str, ranked) -> discord.Embed:
    lines = []
    for i, (uid, (deals, vol)) in enumerate(ranked[:10]):
        rank = MEDALS[i] if i < 3 else f"`{i + 1}.`"
        lines.append(f"{rank} <@{uid}> • **${vol:,.2f}** • {deals} deals")
    embed = discord.Embed(title=f"{BRAND} — {title}", description="\n".join(lines) or "No deals yet.",
                          color=EMBED_COLOR)
    return embed


def _finite(*values: float):
    for v in values:
        if not math.isfinite(v):
            raise commands.BadArgument("Numbers must be finite.")


class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================ BOARDS
    @commands.hybrid_command(name="lb", description="Leaderboard (since the last reset)")
    @commands.guild_only()
    async def lb(self, ctx: commands.Context, board: Literal["users", "staff"] = "users"):
        epoch = await get_epoch(ctx.guild.id)
        ranked = await board_data(ctx.guild.id, board, epoch, include_manual=True)
        title = "Top Exchangers" if board == "users" else "Top Staff"
        await ctx.send(embed=render_board(title, ranked), allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="clb", description="Leaderboard for the current month")
    @commands.guild_only()
    async def clb(self, ctx: commands.Context, board: Literal["users", "staff"] = "users"):
        epoch = await get_epoch(ctx.guild.id)
        since = max(epoch, month_start())
        ranked = await board_data(ctx.guild.id, board, since, include_manual=False)
        title = ("Top Exchangers" if board == "users" else "Top Staff") + " (this month)"
        await ctx.send(embed=render_board(title, ranked), allowed_mentions=discord.AllowedMentions.none())

    # =========================================================== PROFILE
    @commands.hybrid_command(name="p", aliases=["profile"], description="View an exchange profile")
    @commands.guild_only()
    async def profile(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        user = user or ctx.author
        gid = ctx.guild.id
        epoch = await get_epoch(gid)

        ranked = await board_data(gid, "users", epoch, include_manual=True)
        deals, vol, rank = 0, 0.0, None
        for i, (uid, (d, v)) in enumerate(ranked, start=1):
            if uid == user.id:
                deals, vol, rank = d, v, i

        all_time = await db.fetchone(
            "SELECT COUNT(*) AS d, COALESCE(SUM(amount_usd), 0) AS v FROM tickets "
            "WHERE guild_id=? AND kind='exchange' AND completed=1 AND user_id=?", (gid, user.id))
        handled = await db.fetchone(
            "SELECT COUNT(*) AS d FROM tickets WHERE guild_id=? AND kind='exchange' AND completed=1 AND claimed_by=?",
            (gid, user.id))
        vouches = await db.fetchone(
            "SELECT COUNT(*) AS c FROM vouches WHERE guild_id=? AND user_id=?", (gid, user.id))

        embed = discord.Embed(title=f"{user.display_name}'s Profile", color=EMBED_COLOR)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Rank (current board)", value=f"#{rank}" if rank else "Unranked")
        embed.add_field(name="Deals (current board)", value=str(deals))
        embed.add_field(name="Volume (current board)", value=f"${vol:,.2f}")
        embed.add_field(name="All-time deals", value=f"{all_time['d']} (${all_time['v']:,.2f})")
        embed.add_field(name="Deals handled as staff", value=str(handled["d"]))
        embed.add_field(name="Vouches", value=str(vouches["c"]))
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="deals", description="Show a user's completed deals")
    @commands.guild_only()
    async def deals(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        user = user or ctx.author
        rows = await db.fetchall(
            "SELECT id, user_id, claimed_by, amount_usd, send_asset, recv_asset, completed_at FROM tickets "
            "WHERE guild_id=? AND kind='exchange' AND completed=1 AND (user_id=? OR claimed_by=?) "
            "ORDER BY completed_at DESC LIMIT 10",
            (ctx.guild.id, user.id, user.id),
        )
        if not rows:
            return await ctx.send("No completed deals found.", ephemeral=True)
        lines = []
        for r in rows:
            role = "Client" if r["user_id"] == user.id else "Handler"
            lines.append(f"`#{r['id']:04d}` • ${r['amount_usd']:,.2f} • {r['send_asset']} -> {r['recv_asset']} "
                         f"• {role} • {r['completed_at'][:10]}")
        embed = discord.Embed(title=f"{user.display_name}'s last deals", description="\n".join(lines), color=EMBED_COLOR)
        await ctx.send(embed=embed)

    # ============================================================ VOUCH
    @commands.hybrid_command(name="e", description="Add an exchange vouch / rep point for a user")
    @require("exchanger")
    @commands.guild_only()
    async def vouch_add(self, ctx: commands.Context, user: discord.Member, *, note: str = "No note"):
        if user.id == ctx.author.id:
            raise commands.BadArgument("You can't vouch for yourself.")
        await db.insert(
            "INSERT INTO vouches (guild_id, user_id, given_by, note) VALUES (?, ?, ?, ?)",
            (ctx.guild.id, user.id, ctx.author.id, note[:200]),
        )
        count = await db.fetchone("SELECT COUNT(*) AS c FROM vouches WHERE guild_id=? AND user_id=?",
                                  (ctx.guild.id, user.id))
        await ctx.send(f"⭐ Vouch added for {user.mention}. They now have **{count['c']}** vouches.")

    # ============================================================== TAX
    @commands.hybrid_command(name="mytax", description="Show the tax you currently owe")
    @require("exchanger")
    @commands.guild_only()
    async def mytax(self, ctx: commands.Context):
        row = await db.fetchone(
            "SELECT COUNT(*) AS d, COALESCE(SUM(amount_usd), 0) AS v, COALESCE(SUM(tax_usd), 0) AS t "
            "FROM tickets WHERE guild_id=? AND claimed_by=? AND completed=1 AND tax_cleared=0",
            (ctx.guild.id, ctx.author.id),
        )
        embed = discord.Embed(title="Your accumulated tax", color=EMBED_COLOR)
        embed.add_field(name="Uncleared deals", value=str(row["d"]))
        embed.add_field(name="Volume", value=f"${row['v']:,.2f}")
        embed.add_field(name="Tax owed", value=f"${row['t']:,.4f}")
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="stafffees", description="Show tax owed by every staff member")
    @require("manager")
    @commands.guild_only()
    async def stafffees(self, ctx: commands.Context):
        rows = await db.fetchall(
            "SELECT claimed_by AS uid, COUNT(*) AS d, COALESCE(SUM(tax_usd), 0) AS t FROM tickets "
            "WHERE guild_id=? AND completed=1 AND tax_cleared=0 AND claimed_by IS NOT NULL "
            "GROUP BY claimed_by ORDER BY t DESC",
            (ctx.guild.id,),
        )
        lines = [f"<@{r['uid']}> • {r['d']} deals • **${r['t']:,.4f}**" for r in rows]
        embed = discord.Embed(title="Staff fees owed", description="\n".join(lines) or "Nothing owed.", color=EMBED_COLOR)
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="cleartax", description="Mark a staff member's tax as paid")
    @require("manager")
    @commands.guild_only()
    async def cleartax(self, ctx: commands.Context, user: discord.Member):
        row = await db.fetchone(
            "SELECT COALESCE(SUM(tax_usd), 0) AS t FROM tickets "
            "WHERE guild_id=? AND claimed_by=? AND completed=1 AND tax_cleared=0", (ctx.guild.id, user.id))
        changed = await db.execute(
            "UPDATE tickets SET tax_cleared=1 WHERE guild_id=? AND claimed_by=? AND completed=1 AND tax_cleared=0",
            (ctx.guild.id, user.id),
        )
        await ctx.send(f"✅ Cleared **${row['t']:,.4f}** across {changed} deals for {user.mention}.")

    # ===================================== MANUAL LEADERBOARD EDITS ⚠️
    @commands.hybrid_command(name="addlb", description="Add deals and volume to a user's leaderboard stats")
    @require("manager")
    @commands.guild_only()
    async def addlb(self, ctx: commands.Context, user: discord.Member, deals: int, volume_usd: float):
        _finite(volume_usd)
        await db.execute(
            "INSERT INTO manual_stats (guild_id, user_id, deals, volume_usd) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "deals = manual_stats.deals + excluded.deals, volume_usd = manual_stats.volume_usd + excluded.volume_usd",
            (ctx.guild.id, user.id, deals, volume_usd),
        )
        await ctx.send(f"✅ Added **{deals}** deals and **${volume_usd:,.2f}** to {user.mention}.")

    @commands.hybrid_command(name="setlb", description="Set a user's total leaderboard deals and volume")
    @require("manager")
    @commands.guild_only()
    async def setlb(self, ctx: commands.Context, user: discord.Member, deals: int, volume_usd: float):
        _finite(volume_usd)
        epoch = await get_epoch(ctx.guild.id)
        real = await db.fetchone(
            "SELECT COUNT(*) AS d, COALESCE(SUM(amount_usd), 0) AS v FROM tickets "
            "WHERE guild_id=? AND kind='exchange' AND completed=1 AND user_id=? AND completed_at >= ?",
            (ctx.guild.id, user.id, epoch),
        )
        # manual adjustment = target - what real deals already contribute
        await db.execute(
            "INSERT INTO manual_stats (guild_id, user_id, deals, volume_usd) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET deals=excluded.deals, volume_usd=excluded.volume_usd",
            (ctx.guild.id, user.id, deals - real["d"], volume_usd - real["v"]),
        )
        await ctx.send(f"✅ {user.mention} now shows **{deals}** deals and **${volume_usd:,.2f}** on the leaderboard.")

    @commands.hybrid_command(name="resetlb", description="Reset the leaderboard (deal history is kept)")
    @require("manager")
    @commands.guild_only()
    async def resetlb(self, ctx: commands.Context):
        gid = ctx.guild.id

        async def do_reset(interaction: discord.Interaction):
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            await db.set_setting(gid, "lb_epoch", now)
            await db.execute("DELETE FROM manual_stats WHERE guild_id=?", (gid,))
            await interaction.edit_original_response(content="✅ Leaderboard reset. Deal history and tickets are untouched.")

        await ctx.send(
            "⚠️ This starts a **new leaderboard** and clears manual edits. Completed deals stay in the database "
            "(`,deals` still shows them). Confirm?",
            view=ConfirmView(ctx.author.id, do_reset),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
