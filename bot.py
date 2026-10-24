# bot.py
import os
import traceback
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import database
from config import PREFIX

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True      # needed for ',' commands and transcripts

EXTENSIONS = (
    "cogs.setup_cog",
    "cogs.exchange",
    "cogs.support",
    "cogs.ticket_commands",
    "cogs.stats",
    "cogs.calculators",
)

WRAPPERS = (commands.CommandInvokeError, commands.HybridCommandError, app_commands.CommandInvokeError)


class ExchangeBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,                                   # we have our own ,help
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False),
        )

    async def setup_hook(self):
        await database.init_db()
        for ext in EXTENSIONS:
            await self.load_extension(ext)

        dev_guild = os.getenv("DEV_GUILD_ID")
        if dev_guild:                                            # instant slash sync for testing
            guild = discord.Object(id=int(dev_guild))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        while isinstance(error, WRAPPERS):
            error = error.original

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.NoPrivateMessage):
            msg = "This command only works in a server."
        elif isinstance(error, commands.MissingPermissions):
            msg = "You need the **Administrator** permission for that."
        elif isinstance(error, (commands.CheckFailure, app_commands.CheckFailure)):
            msg = str(error) or "You can't use that command."
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = f"Missing `{error.param.name}`.\nUsage: `{PREFIX}{ctx.command.qualified_name} {ctx.command.signature}`"
        elif isinstance(error, commands.UserInputError):
            msg = f"{error}\nUsage: `{PREFIX}{ctx.command.qualified_name} {ctx.command.signature}`"
        else:
            traceback.print_exception(type(error), error, error.__traceback__)
            msg = "Something went wrong. The error was logged."

        try:
            await ctx.send(msg, ephemeral=True)
        except discord.HTTPException:
            pass


bot = ExchangeBot()

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
