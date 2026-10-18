from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
import database as db
from config import BRAND, EMBED_COLOR

MEDALS = ["🥇", "🥈", "🥉"]

class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Top exchangers or top staff")
    @app_commands.describe(board="Which leaderboard to show")
    @app_commands.choices(board=[
        app_commands.Choice(name="Customers (by volume)", value="users"),
        app_commands.Choice(name="Staff (deals handled)", value="staff"),
    ])
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction,
                          board: Optional[app_commands.Choice[str]] = None):
        which = board.value if board else "users"
        column = "user_id" if which == "users" else "claimed_by"

        rows = await db.fetchall(
            f"SELECT {column} AS uid, COUNT(*) AS deals, SUM(volume_inr) AS vol "
            f"FROM tickets WHERE guild_id=? AND kind='exchange' AND completed=1 "
            f"AND {column} IS NOT NULL GROUP BY {column} ORDER BY vol DESC LIMIT 10",
            (interaction.guild_id,),
        )

        if not rows:
            return await interaction.response.send_message("No completed deals yet.", ephemeral=True)

        lines = []
        for i, r in enumerate(rows):
            rank = MEDALS[i] if i < 3 else f"`{i + 1}.`"
            lines.append(f"{rank} <@{r['uid']}> - ₹{r['vol']:,.0f} ({r['deals']} deals)")

        title = "Top Exchangers" if which == "users" else "Top Staff"
        embed = discord.Embed(title=f"{BRAND} - {title}", description="\n".join(lines), color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="profile", description="Show exchange stats for a user")
    @app_commands.describe(user="Leave empty to see your own")
    @app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        user = user or interaction.user
        row = await db.fetchone(
            "SELECT COUNT(*) AS deals, COALESCE(SUM(volume_inr), 0) AS vol, MAX(created_at) AS last "
            "FROM tickets WHERE guild_id=? AND user_id=? AND kind='exchange' AND completed=1",
            (interaction.guild_id, user.id),
        )
        embed = discord.Embed(title=f"{user.display_name}'s Profile", color=EMBED_COLOR)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Completed deals", value=str(row["deals"]))
        embed.add_field(name="Total volume", value=f"₹{row['vol']:,.0f}")
        embed.add_field(name="Last deal", value=row["last"] or "None")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
