# cogs/setup_cog.py
import math
from typing import Literal
import discord
from discord.ext import commands

import database as db
from config import PREFIX, ROLE_KINDS, DEFAULT_RATES
from utils.checks import require, role_ids_for
from utils.calc import get_rate, get_c2c_fee, get_tax_percent

Kind = Literal["exchanger", "support", "application", "middleman", "manager"]


def _positive(value: float):
    if not math.isfinite(value) or value <= 0:
        raise commands.BadArgument("The value must be a positive number.")


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------------------------------------------------- channels
    @commands.hybrid_command(name="setup", description="Set the ticket category and log channels")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def setup_cmd(self, ctx: commands.Context,
                        ticket_category: discord.CategoryChannel,
                        deal_log_channel: discord.TextChannel,
                        transcript_channel: discord.TextChannel):
        gid = ctx.guild.id
        await db.set_setting(gid, "ticket_category", ticket_category.id)
        await db.set_setting(gid, "deal_log_channel", deal_log_channel.id)
        await db.set_setting(gid, "transcript_channel", transcript_channel.id)
        await ctx.send(
            f"✅ Saved.\nTicket category: **{ticket_category.name}**\n"
            f"Deal logs: {deal_log_channel.mention}\nTranscripts: {transcript_channel.mention}\n\n"
            f"Next: add roles with `{PREFIX}addrole <kind> @role`, then post the panels.",
            ephemeral=True,
        )

    # ------------------------------------------------------------- roles
    @commands.hybrid_command(name="addrole", description="Give a role a permission kind")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def addrole(self, ctx: commands.Context, kind: Kind, role: discord.Role):
        changed = await db.execute(
            "INSERT OR IGNORE INTO role_perms (guild_id, kind, role_id) VALUES (?, ?, ?)",
            (ctx.guild.id, kind, role.id),
        )
        text = "✅ Added" if changed else "ℹ️ Already set"
        await ctx.send(f"{text}: {role.mention} is now **{kind}**.\n> {ROLE_KINDS[kind]}",
                       ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="removerole", description="Remove a role from a permission kind")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def removerole(self, ctx: commands.Context, kind: Kind, role: discord.Role):
        changed = await db.execute(
            "DELETE FROM role_perms WHERE guild_id=? AND kind=? AND role_id=?",
            (ctx.guild.id, kind, role.id),
        )
        await ctx.send("✅ Removed." if changed else "That role wasn't set for that kind.",
                       ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="roles", description="Show which roles have which permissions")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def roles(self, ctx: commands.Context):
        embed = discord.Embed(title="Role permissions", color=0x2B2D31)
        for kind, desc in ROLE_KINDS.items():
            ids = await role_ids_for(ctx.guild.id, kind)
            value = " ".join(f"<@&{i}>" for i in ids) or "*none set*"
            embed.add_field(name=f"{kind}", value=f"{desc}\n{value}", inline=False)
        await ctx.send(embed=embed, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    # ------------------------------------------------------------- rates
    @commands.hybrid_command(name="setrate", description="Set the INR rate per $1")
    @require("manager")
    @commands.guild_only()
    async def setrate(self, ctx: commands.Context, ex_type: Literal["inr_to_crypto", "crypto_to_inr"], value: float):
        _positive(value)
        await db.set_setting(ctx.guild.id, f"rate_{ex_type}", value)
        await ctx.send(f"✅ `{ex_type}` rate is now **{value:g} / $**. "
                       f"Existing tickets keep the rate they were opened with.")

    @commands.hybrid_command(name="setfee", description="Set the crypto-to-crypto fee percent")
    @require("manager")
    @commands.guild_only()
    async def setfee(self, ctx: commands.Context, percent: float):
        if not math.isfinite(percent) or not 0 <= percent < 100:
            raise commands.BadArgument("Percent must be between 0 and 100.")
        await db.set_setting(ctx.guild.id, "fee_crypto_to_crypto", percent)
        await ctx.send(f"✅ Crypto to Crypto fee is now **{percent:g}%**.")

    @commands.hybrid_command(name="settax", description="Set the staff tax percent")
    @require("manager")
    @commands.guild_only()
    async def settax(self, ctx: commands.Context, percent: float):
        if not math.isfinite(percent) or not 0 <= percent < 100:
            raise commands.BadArgument("Percent must be between 0 and 100.")
        await db.set_setting(ctx.guild.id, "tax_percent", percent)
        await ctx.send(f"✅ Staff tax is now **{percent:g}%** of each completed deal.")


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
