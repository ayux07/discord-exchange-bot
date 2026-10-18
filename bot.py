import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import database

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

EXTENSIONS = (
    "cogs.setup_cog",
    "cogs.exchange",
    "cogs.stats",
    "cogs.support",
)

class ExchangeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await database.init_db()

        for ext in EXTENSIONS:
            await self.load_extension(ext)

        dev_guild = os.getenv("DEV_GUILD_ID")
        if dev_guild:
            guild = discord.Object(id=int(dev_guild))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

bot = ExchangeBot()

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
