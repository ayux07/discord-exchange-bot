# cogs/calculators.py
import math
from typing import Literal

import discord
from discord.ext import commands

from config import EMBED_COLOR, EX_TYPES, INR_METHODS, CRYPTOS
from utils.calc import calculate, get_rate, get_c2c_fee, get_tax_percent


class Calculators(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="calc", description="Calculate an exchange")
    @commands.guild_only()
    async def calc(self, ctx: commands.Context,
                   ex_type: Literal["inr_to_crypto", "crypto_to_inr", "crypto_to_crypto"],
                   amount: float,
                   send_asset: str,
                   recv_asset: str):
        if ex_type not in EX_TYPES or not EX_TYPES[ex_type]["enabled"]:
            return await ctx.send("That exchange type is disabled.", ephemeral=True)
        if not math.isfinite(amount) or amount <= 0:
            raise commands.BadArgument("Amount must be a positive number.")

        send = send_asset.upper()
        recv = recv_asset.upper()
        if send not in INR_METHODS and send not in CRYPTOS:
            return await ctx.send(f"Unknown send asset `{send}`.", ephemeral=True)
        if recv not in INR_METHODS and recv not in CRYPTOS:
            return await ctx.send(f"Unknown receive asset `{recv}`.", ephemeral=True)

        calc = await calculate(ctx.guild.id, ex_type, amount, send, recv)
        if "error" in calc:
            return await ctx.send(calc["error"], ephemeral=True)

        embed = discord.Embed(title=f"{EX_TYPES[ex_type]['panel_title']} Calculator", color=EMBED_COLOR)
        embed.add_field(name="Amount", value=f"`${amount:,.2f}`")
        embed.add_field(name="Exchange", value=f"`{send} -> {recv}`")
        embed.add_field(name="Result", value=f"`{calc['calc_text']}`", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rates", description="Show the current exchange rates")
    @commands.guild_only()
    async def rates(self, ctx: commands.Context):
        embed = discord.Embed(title="Current rates", color=EMBED_COLOR)
        embed.add_field(name="INR to Crypto", value=f"`{await get_rate(ctx.guild.id, 'inr_to_crypto'):g} INR / $`")
        embed.add_field(name="Crypto to INR", value=f"`{await get_rate(ctx.guild.id, 'crypto_to_inr'):g} INR / $`")
        embed.add_field(name="Crypto to Crypto fee", value=f"`{await get_c2c_fee(ctx.guild.id):g}%`")
        embed.add_field(name="Staff tax", value=f"`{await get_tax_percent(ctx.guild.id):g}%`")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping", description="Check the bot's latency")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"🏓 Pong! `{round(self.bot.latency * 1000)}ms`")

    @commands.hybrid_command(name="help", description="List every command")
    async def help_cmd(self, ctx: commands.Context):
        embed = discord.Embed(title="Commands", color=EMBED_COLOR)
        embed.add_field(name="Everyone", inline=False, value=(
            "`,calc` • `,rates` • `,lb` • `,clb` • `,p` • `,deals` • `,help` • `,ping`\n"
            "Ticket: `,claim` • `,uc` • `,close` • `,transcript` • `,v` • `,3p`"))
        embed.add_field(name="Staff", inline=False, value=(
            "`,mytax` • `,e` (vouch)"))
        embed.add_field(name="Managers", inline=False, value=(
            "`,exchangepanel` • `,supportpanel` • `,applypanel` • `,setrate` • `,setfee` • `,settax`\n"
            "`,stafffees` • `,cleartax` • `,addlb` • `,setlb` • `,resetlb`"))
        embed.add_field(name="Admins", inline=False, value=(
            "`,setup` • `,addrole` • `,removerole` • `,roles`"))
        embed.set_footer(text="All commands also work as slash commands.")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Calculators(bot))
