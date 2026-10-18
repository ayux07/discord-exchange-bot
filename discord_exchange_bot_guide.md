# Build a Discord Exchange Ticket Bot (Step by Step)

A complete guide to building an **INR ↔ Crypto exchange ticket bot** in Python with `discord.py`: dropdown panel, payment/crypto pickers, details form, private ticket channels, claim/complete/close buttons, auto-calculated fees, HTML transcripts, deal logs, leaderboard, profiles, support tickets and staff applications.

> **What this bot does and does not do.** It automates the *workflow*: tickets, calculations, logging, stats. The actual money and crypto transfers are done **manually by your staff**. Automatic blockchain verification is an advanced add-on, covered briefly in Part 17.

---

## Table of Contents

1. [How the whole system works](#part-1-how-the-whole-system-works)
2. [Prerequisites](#part-2-prerequisites)
3. [Create the bot on Discord](#part-3-create-the-bot-on-discord)
4. [Invite the bot to your server](#part-4-invite-the-bot-to-your-server)
5. [Set up the project](#part-5-set-up-the-project)
6. [Configuration file](#part-6-configuration-file)
7. [Database layer](#part-7-database-layer)
8. [Utility modules](#part-8-utility-modules) (checks, rates, calculator, transcript, shared ticket logic)
9. [Main bot file](#part-9-main-bot-file)
10. [Setup cog (`/setup`)](#part-10-setup-cog)
11. [Exchange cog: panel, pickers, form, ticket](#part-11-exchange-cog)
12. [Stats cog: leaderboard and profile](#part-12-stats-cog)
13. [Support and staff applications cog](#part-13-support-and-applications-cog)
14. [Discord server setup](#part-14-discord-server-setup)
15. [Run and test everything](#part-15-run-and-test)
16. [Deploy for 24/7 uptime](#part-16-deploy-247)
17. [Security, scam protection, legal](#part-17-security-scam-protection-legal)
18. [Optional upgrades](#part-18-optional-upgrades)
19. [Troubleshooting](#part-19-troubleshooting)

---

## Part 1: How the whole system works

### The user flow

```
Panel message (dropdown)
   └─ user picks: INR to Crypto / Crypto to INR / Crypto to Crypto
        └─ private (ephemeral) picker: payment method + crypto
             └─ "Continue" opens a form (amount + payout details)
                  └─ bot calculates fee + amount using live rates
                       └─ bot creates a private ticket channel
                            └─ staff: Claim → handle deal → Complete Deal → Close
                                 └─ bot saves transcript, posts deal log, updates stats
```

### Project architecture

| Piece | Purpose |
|---|---|
| `bot.py` | Starts the bot, loads cogs, syncs slash commands |
| `config.py` | Brand name, fees, minimum amounts, payment methods, coins |
| `database.py` | SQLite storage (settings, tickets, deals) |
| `utils/checks.py` | "Is this person staff?" helper |
| `utils/rates.py` | Fetches live prices from CoinGecko, with caching |
| `utils/calc.py` | Fee and amount calculation for the 3 exchange types |
| `utils/transcript.py` | Turns a channel's history into an HTML file |
| `utils/tickets.py` | Shared logic: create ticket channel, claim, close |
| `cogs/setup_cog.py` | `/setup` command to store roles and channels |
| `cogs/exchange.py` | The main exchange panel and ticket workflow |
| `cogs/stats.py` | `/leaderboard`, `/profile` |
| `cogs/support.py` | Support tickets and staff applications |

### Key concepts you will use

- **Cog**: a class that groups related commands and listeners.
- **View**: a set of buttons or dropdowns attached to a message.
- **Persistent view**: a view with `timeout=None` and fixed `custom_id`s, re-registered on startup so buttons still work after a restart.
- **Modal**: a popup form.
- **Ephemeral message**: a message only the clicking user can see.
- **Interaction**: what Discord sends when someone uses a slash command, button, dropdown or form. You must respond within **3 seconds** (use `defer()` for slow work).

---

## Part 2: Prerequisites

1. **Python 3.10 or newer.** Check with `python --version` (or `python3 --version`).
2. **A Discord account** with a server where you have admin rights. Create a **separate test server** first.
3. **A code editor** such as VS Code.
4. **Developer Mode in Discord** (to copy IDs): User Settings → Advanced → Developer Mode.

---

## Part 3: Create the bot on Discord

1. Open <https://discord.com/developers/applications> and click **New Application**. Name it and accept the terms.
2. In the left sidebar open **Bot**.
3. Click **Reset Token**, then copy the token and save it somewhere safe. **Never share it or upload it to GitHub.** If it leaks, reset it immediately.
4. Scroll to **Privileged Gateway Intents** and turn on **Message Content Intent**. This is required so transcripts can read message text.
5. Turn **Public Bot** off unless you want others to add it.
6. Click **Save Changes**.

> Bots in 100+ servers need Discord verification to keep the Message Content intent. For one server this does not matter.

---

## Part 4: Invite the bot to your server

1. Go to **OAuth2 → URL Generator**.
2. **Scopes:** tick `bot` and `applications.commands`.
3. **Bot Permissions:** tick only what you need (do **not** give Administrator):
   - View Channels
   - Manage Channels (creates and deletes ticket channels)
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Mention Everyone (optional, so it can ping a staff role that is not mentionable)
4. Copy the generated URL, open it in your browser, choose your server and click **Authorize**.

The bot appears offline until you run the code.

---

## Part 5: Set up the project

### 5.1 Create the folder and virtual environment

```bash
mkdir exchange-bot
cd exchange-bot
python -m venv venv
```

Activate it:

```bash
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### 5.2 Create the folder structure

```
exchange-bot/
├── .env
├── .gitignore
├── requirements.txt
├── bot.py
├── config.py
├── database.py
├── utils/
│   ├── __init__.py
│   ├── checks.py
│   ├── rates.py
│   ├── calc.py
│   ├── transcript.py
│   └── tickets.py
└── cogs/
    ├── __init__.py
    ├── setup_cog.py
    ├── exchange.py
    ├── stats.py
    └── support.py
```

On macOS/Linux:

```bash
mkdir utils cogs
touch utils/__init__.py cogs/__init__.py
```

### 5.3 `requirements.txt`

```
discord.py>=2.4
python-dotenv>=1.0
aiosqlite>=0.20
```

(`aiohttp` is installed automatically with discord.py.)

```bash
pip install -r requirements.txt
```

### 5.4 `.env`

```
DISCORD_TOKEN=paste_your_bot_token_here
DEV_GUILD_ID=paste_your_test_server_id_here
```

`DEV_GUILD_ID` makes slash commands appear instantly in your test server. Right-click the server icon → Copy Server ID.

### 5.5 `.gitignore`

```
.env
venv/
__pycache__/
*.db
```

---

## Part 6: Configuration file

Create `config.py`. Everything you might want to tweak lives here.

```python
# config.py

BRAND = "Atrix Exchange"          # change to your brand name
EMBED_COLOR = 0x5865F2

# Exchange types. "min" is in INR for the INR types and in USD for crypto_to_crypto.
EX_TYPES = {
    "inr_to_crypto": {
        "label": "INR to Crypto",
        "slug": "inr-crypto",
        "fee": 6.0,      # percent
        "min": 100,      # INR
        "unit": "INR",
    },
    "crypto_to_inr": {
        "label": "Crypto to INR",
        "slug": "crypto-inr",
        "fee": 5.0,
        "min": 100,      # INR value of the crypto
        "unit": "INR",
    },
    "crypto_to_crypto": {
        "label": "Crypto to Crypto",
        "slug": "crypto-crypto",
        "fee": 3.0,
        "min": 10,       # USD value
        "unit": "USD",
    },
}

INR_METHODS = [
    "UPI", "Bank Transfer", "IMPS", "Omnicard", "Mobikwik",
    "Google Pay", "PhonePe", "Paytm", "Fampay",
]

# Symbols must also exist in utils/rates.py COIN_IDS
CRYPTOS = ["LTC", "USDT", "BTC", "ETH", "TRX"]
```

How amounts work:

| Type | "Amount" the user types | Fee applied to | User receives |
|---|---|---|---|
| INR to Crypto | INR they send | INR amount | (amount − fee) ÷ coin price in INR |
| Crypto to INR | INR **value** of the crypto they send | INR amount | amount − fee, in INR |
| Crypto to Crypto | USD value of what they send | USD amount | (amount − fee) ÷ receive coin price in USD |

---

## Part 7: Database layer

Create `database.py`. It uses SQLite through `aiosqlite` so database calls never block the bot.

```python
# database.py
import aiosqlite

DB_PATH = "exchange.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER NOT NULL,
    key      TEXT NOT NULL,
    value    TEXT NOT NULL,
    PRIMARY KEY (guild_id, key)
);

CREATE TABLE IF NOT EXISTS tickets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id       INTEGER NOT NULL,
    channel_id     INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    kind           TEXT NOT NULL,              -- 'exchange' or 'support'
    ex_type        TEXT,
    method         TEXT,
    crypto         TEXT,
    amount         REAL,
    fee            REAL,
    receive_amount REAL,
    rate           REAL,
    payout_details TEXT,
    volume_inr     REAL DEFAULT 0,
    claimed_by     INTEGER,
    status         TEXT NOT NULL DEFAULT 'open',   -- 'open' or 'closed'
    completed      INTEGER NOT NULL DEFAULT 0,     -- 1 = deal finished
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_tickets_channel ON tickets(channel_id);
CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(guild_id, user_id);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def insert(query, params=()):
    """Run an INSERT and return the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        await db.commit()
        return cur.lastrowid


async def execute(query, params=()):
    """Run an UPDATE/DELETE and return how many rows changed."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        await db.commit()
        return cur.rowcount


async def fetchone(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return await cur.fetchone()


async def fetchall(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return await cur.fetchall()


async def get_setting(guild_id, key):
    row = await fetchone(
        "SELECT value FROM settings WHERE guild_id=? AND key=?", (guild_id, key)
    )
    return row["value"] if row else None


async def set_setting(guild_id, key, value):
    await execute(
        "INSERT INTO settings (guild_id, key, value) VALUES (?, ?, ?) "
        "ON CONFLICT(guild_id, key) DO UPDATE SET value=excluded.value",
        (guild_id, key, str(value)),
    )
```

Why `completed` is separate from `status`: a ticket can be *completed* (deal done, counts toward leaderboard) while still *open* (channel not closed yet).

---

## Part 8: Utility modules

### 8.1 `utils/checks.py`

```python
# utils/checks.py
import discord
import database as db


async def is_staff(interaction: discord.Interaction) -> bool:
    """True for server admins and members with the configured staff role."""
    user = interaction.user
    if not isinstance(user, discord.Member):
        return False
    if user.guild_permissions.administrator:
        return True
    role_id = await db.get_setting(interaction.guild_id, "staff_role")
    if role_id is None:
        return False
    return any(r.id == int(role_id) for r in user.roles)
```

### 8.2 `utils/rates.py`

Pulls prices from CoinGecko's free API and caches them for 60 seconds so you never hit rate limits.

```python
# utils/rates.py
import time
import aiohttp

COIN_IDS = {
    "BTC": "bitcoin",
    "LTC": "litecoin",
    "USDT": "tether",
    "ETH": "ethereum",
    "TRX": "tron",
}

API_URL = "https://api.coingecko.com/api/v3/simple/price"
CACHE_SECONDS = 60          # refresh at most once a minute
MAX_STALE_SECONDS = 15 * 60  # refuse to use prices older than 15 minutes


class RateService:
    def __init__(self):
        self._data = None
        self._fetched_at = 0.0

    async def _refresh(self):
        params = {"ids": ",".join(COIN_IDS.values()), "vs_currencies": "inr,usd"}
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(API_URL, params=params) as resp:
                resp.raise_for_status()
                self._data = await resp.json()
                self._fetched_at = time.time()

    async def price(self, symbol: str, currency: str) -> float:
        age = time.time() - self._fetched_at
        if self._data is None or age > CACHE_SECONDS:
            try:
                await self._refresh()
            except Exception:
                # Fall back to cached prices only if they are not too old
                if self._data is None or age > MAX_STALE_SECONDS:
                    raise
        return float(self._data[COIN_IDS[symbol]][currency.lower()])


rates = RateService()
```

### 8.3 `utils/calc.py`

```python
# utils/calc.py
from utils.rates import rates


def fmt_crypto(value: float) -> str:
    return f"{value:,.8f}".rstrip("0").rstrip(".")


async def calculate(ex_type: str, amount: float, method: str, crypto: str, fee_pct: float) -> dict:
    """
    method / crypto meaning per type:
      inr_to_crypto    : method = INR method used to pay,   crypto = coin to receive
      crypto_to_inr    : method = INR method to receive,    crypto = coin being sent
      crypto_to_crypto : method = coin being sent,          crypto = coin to receive
    """
    usdt_inr = await rates.price("USDT", "inr")   # used as the USD/INR proxy
    fee_factor = fee_pct / 100

    if ex_type == "inr_to_crypto":
        price = await rates.price(crypto, "inr")
        fee = amount * fee_factor
        receive = (amount - fee) / price
        return {
            "send_text": f"₹{amount:,.2f} via {method}",
            "fee_text": f"₹{fee:,.2f} ({fee_pct}%)",
            "receive_text": f"{fmt_crypto(receive)} {crypto}",
            "rate_text": f"1 {crypto} = ₹{price:,.2f}",
            "fee": fee, "receive": receive, "rate": price,
            "volume_inr": amount,
        }

    if ex_type == "crypto_to_inr":
        price = await rates.price(crypto, "inr")
        send = amount / price
        fee = amount * fee_factor
        receive = amount - fee
        return {
            "send_text": f"{fmt_crypto(send)} {crypto} (≈ ₹{amount:,.2f})",
            "fee_text": f"₹{fee:,.2f} ({fee_pct}%)",
            "receive_text": f"₹{receive:,.2f} via {method}",
            "rate_text": f"1 {crypto} = ₹{price:,.2f}",
            "fee": fee, "receive": receive, "rate": price,
            "volume_inr": amount,
        }

    # crypto_to_crypto (amount is in USD)
    send_price = await rates.price(method, "usd")
    recv_price = await rates.price(crypto, "usd")
    send = amount / send_price
    fee = amount * fee_factor
    receive = (amount - fee) / recv_price
    return {
        "send_text": f"{fmt_crypto(send)} {method} (≈ ${amount:,.2f})",
        "fee_text": f"${fee:,.2f} ({fee_pct}%)",
        "receive_text": f"{fmt_crypto(receive)} {crypto}",
        "rate_text": f"1 {method} = ${send_price:,.2f} | 1 {crypto} = ${recv_price:,.2f}",
        "fee": fee, "receive": receive, "rate": recv_price,
        "volume_inr": amount * usdt_inr,
    }
```

### 8.4 `utils/transcript.py`

Builds a readable HTML file from the channel history. Everything is HTML-escaped so nobody can inject scripts into your transcripts.

```python
# utils/transcript.py
import html
import discord


async def build_transcript(channel: discord.TextChannel) -> bytes:
    rows = []
    async for m in channel.history(limit=None, oldest_first=True):
        ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        author = html.escape(f"{m.author} ({m.author.id})")
        body = html.escape(m.content or "").replace("\n", "<br>")

        extras = []
        for a in m.attachments:
            url, name = html.escape(a.url), html.escape(a.filename)
            extras.append(f'<div class="att">📎 <a href="{url}">{name}</a></div>')

        for e in m.embeds:
            parts = []
            if e.title:
                parts.append(f"<b>{html.escape(e.title)}</b>")
            if e.description:
                parts.append(html.escape(e.description).replace("\n", "<br>"))
            for f in e.fields:
                parts.append(
                    f"<b>{html.escape(f.name)}:</b> "
                    f"{html.escape(f.value).replace(chr(10), '<br>')}"
                )
            extras.append('<div class="embed">' + "<br>".join(parts) + "</div>")

        rows.append(
            f'<div class="msg"><div class="meta"><b>{author}</b> '
            f'<span class="ts">{ts}</span></div>'
            f'<div>{body}</div>{"".join(extras)}</div>'
        )

    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Transcript - {html.escape(channel.name)}</title>
<style>
body {{ background:#313338; color:#dbdee1; font-family:Arial,sans-serif; padding:20px; }}
.msg {{ padding:8px 0; border-bottom:1px solid #3f4147; }}
.meta {{ margin-bottom:2px; }} .ts {{ color:#949ba4; font-size:12px; margin-left:8px; }}
.embed {{ border-left:4px solid #5865F2; background:#2b2d31; padding:8px; margin-top:4px; }}
.att a {{ color:#00a8fc; }}
</style></head><body>
<h2>#{html.escape(channel.name)}</h2>
<p>{len(rows)} messages</p>
{"".join(rows)}
</body></html>"""
    return page.encode("utf-8")
```

### 8.5 `utils/tickets.py`

Shared logic used by exchange tickets **and** support tickets.

```python
# utils/tickets.py
import asyncio
import io
import discord
import database as db
from utils.checks import is_staff
from utils.transcript import build_transcript
from config import BRAND, EMBED_COLOR


async def get_ticket(channel_id: int):
    return await db.fetchone("SELECT * FROM tickets WHERE channel_id=?", (channel_id,))


async def create_ticket_channel(guild: discord.Guild, member: discord.Member,
                                name: str, topic: str | None = None) -> discord.TextChannel:
    """Create a private channel visible only to the member, staff and the bot."""
    base = dict(view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(**base),
        guild.me: discord.PermissionOverwrite(**base, manage_channels=True, embed_links=True),
    }

    staff_role_id = await db.get_setting(guild.id, "staff_role")
    if staff_role_id:
        role = guild.get_role(int(staff_role_id))
        if role:
            overwrites[role] = discord.PermissionOverwrite(**base)

    category = None
    category_id = await db.get_setting(guild.id, "ticket_category")
    if category_id:
        category = guild.get_channel(int(category_id))

    return await guild.create_text_channel(
        name=name, overwrites=overwrites, category=category, topic=topic
    )


async def claim_ticket(interaction: discord.Interaction) -> bool:
    """Returns True if the claim succeeded. Sends its own error message otherwise."""
    if not await is_staff(interaction):
        await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
        return False

    # Atomic: only succeeds if nobody has claimed it yet
    changed = await db.execute(
        "UPDATE tickets SET claimed_by=? WHERE channel_id=? AND claimed_by IS NULL",
        (interaction.user.id, interaction.channel_id),
    )
    if not changed:
        await interaction.response.send_message(
            "This ticket is already claimed (or is not a ticket).", ephemeral=True
        )
        return False
    return True


class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Yes, close it", style=discord.ButtonStyle.danger)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Closing ticket...", view=None)
        await close_ticket(interaction.channel, interaction.user)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled.", view=None)


async def prompt_close(interaction: discord.Interaction):
    ticket = await get_ticket(interaction.channel_id)
    if not ticket:
        return await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)

    if not (await is_staff(interaction) or interaction.user.id == ticket["user_id"]):
        return await interaction.response.send_message(
            "Only staff or the ticket owner can close this.", ephemeral=True
        )

    await interaction.response.send_message(
        "Are you sure you want to close this ticket?", view=ConfirmCloseView(), ephemeral=True
    )


async def close_ticket(channel: discord.TextChannel, closer: discord.abc.User):
    guild = channel.guild
    ticket = await get_ticket(channel.id)

    data = await build_transcript(channel)
    filename = f"transcript-{channel.name}.html"

    if ticket:
        await db.execute(
            "UPDATE tickets SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE id=?",
            (ticket["id"],),
        )

    # 1) Post the transcript to the transcripts channel
    log_id = await db.get_setting(guild.id, "transcript_channel")
    if log_id:
        log_channel = guild.get_channel(int(log_id))
        if log_channel:
            embed = discord.Embed(title="Ticket Closed", color=EMBED_COLOR)
            embed.add_field(name="Channel", value=channel.name)
            embed.add_field(name="Closed by", value=closer.mention)
            if ticket:
                embed.add_field(name="Opened by", value=f"<@{ticket['user_id']}>")
                embed.add_field(name="Claimed by",
                                value=f"<@{ticket['claimed_by']}>" if ticket["claimed_by"] else "Nobody")
            await log_channel.send(
                embed=embed, file=discord.File(io.BytesIO(data), filename=filename)
            )

    # 2) DM the transcript to the ticket owner (best effort, DMs may be closed)
    if ticket:
        member = guild.get_member(ticket["user_id"])
        if member:
            try:
                await member.send(
                    f"Your ticket in **{guild.name}** was closed. Transcript attached.",
                    file=discord.File(io.BytesIO(data), filename=filename),
                )
            except discord.HTTPException:
                pass

    await asyncio.sleep(5)
    await channel.delete(reason=f"Ticket closed by {closer}")
```

---

## Part 9: Main bot file

Create `bot.py`:

```python
# bot.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import database

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True   # needed for transcripts

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

        # Instant sync to a test guild if DEV_GUILD_ID is set, else global sync
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
```

What happens on start: the database tables are created, every cog loads (each cog registers its persistent views), then slash commands sync.

---

## Part 10: Setup cog

`/setup` stores your staff role and channels so you never hardcode IDs. Create `cogs/setup_cog.py`:

```python
# cogs/setup_cog.py
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
```

---

## Part 11: Exchange cog

This is the heart of the bot. Create `cogs/exchange.py`. Read the explanation under the code afterwards.

```python
# cogs/exchange.py
import math
import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import BRAND, EMBED_COLOR, EX_TYPES, INR_METHODS, CRYPTOS
from utils import tickets
from utils.calc import calculate
from utils.checks import is_staff

MENTIONS = discord.AllowedMentions(roles=True, users=True, everyone=False)


# ---------------------------------------------------------------- panel embed
def panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title=BRAND,
        description="**SECURE EXCHANGE SERVICE**\nLive staff, private tickets, fast handling.",
        color=EMBED_COLOR,
    )
    for cfg in EX_TYPES.values():
        embed.add_field(
            name=cfg["label"],
            value=f"> Fee: **{cfg['fee']}%**\n> Min: **{cfg['min']} {cfg['unit']}**",
            inline=False,
        )
    embed.set_footer(text="Select an exchange type below to open a ticket.")
    return embed


# ------------------------------------------------- step 1: exchange-type dropdown
class ExchangeTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=cfg["label"], value=key,
                description=f"Fee: {cfg['fee']}% | Min: {cfg['min']} {cfg['unit']}",
            )
            for key, cfg in EX_TYPES.items()
        ]
        super().__init__(
            placeholder="Choose an exchange type",
            options=options,
            custom_id="exchange:type",   # fixed id = persistent
        )

    async def callback(self, interaction: discord.Interaction):
        ex_type = self.values[0]

        # One open exchange ticket per user
        existing = await db.fetchone(
            "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? "
            "AND kind='exchange' AND status='open'",
            (interaction.guild_id, interaction.user.id),
        )
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: <#{existing['channel_id']}>", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Pick your options, then press **Continue**.",
                view=OptionsView(ex_type), ephemeral=True,
            )

        # Re-send the panel view so the dropdown resets and the same option can be chosen again
        try:
            await interaction.message.edit(view=ExchangePanelView())
        except discord.HTTPException:
            pass


class ExchangePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ExchangeTypeSelect())


# ---------------------------------------- step 2: payment method + crypto pickers
class ChoiceSelect(discord.ui.Select):
    def __init__(self, placeholder: str, choices: list[str], attr: str, row: int):
        super().__init__(
            placeholder=placeholder,
            options=[discord.SelectOption(label=c) for c in choices],
            row=row,
        )
        self.attr = attr

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        setattr(self.view, self.attr, chosen)
        for opt in self.options:               # show the current choice
            opt.default = opt.label == chosen
        await interaction.response.edit_message(view=self.view)


class OptionsView(discord.ui.View):
    def __init__(self, ex_type: str):
        super().__init__(timeout=300)
        self.ex_type = ex_type
        self.method = None
        self.crypto = None

        if ex_type == "crypto_to_crypto":
            self.add_item(ChoiceSelect("Crypto you are SENDING", CRYPTOS, "method", row=0))
            self.add_item(ChoiceSelect("Crypto you want to RECEIVE", CRYPTOS, "crypto", row=1))
        elif ex_type == "inr_to_crypto":
            self.add_item(ChoiceSelect("INR method you will PAY with", INR_METHODS, "method", row=0))
            self.add_item(ChoiceSelect("Crypto you want to RECEIVE", CRYPTOS, "crypto", row=1))
        else:  # crypto_to_inr
            self.add_item(ChoiceSelect("INR method you want to RECEIVE on", INR_METHODS, "method", row=0))
            self.add_item(ChoiceSelect("Crypto you are SENDING", CRYPTOS, "crypto", row=1))

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success, row=2)
    async def go(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.method or not self.crypto:
            return await interaction.response.send_message(
                "Please choose both options first.", ephemeral=True
            )
        if self.ex_type == "crypto_to_crypto" and self.method == self.crypto:
            return await interaction.response.send_message(
                "Sending and receiving coins must be different.", ephemeral=True
            )
        await interaction.response.send_modal(
            DetailsModal(self.ex_type, self.method, self.crypto)
        )


# ------------------------------------------------------ step 3: the details form
class DetailsModal(discord.ui.Modal):
    def __init__(self, ex_type: str, method: str, crypto: str):
        super().__init__(title="Exchange details")
        self.ex_type, self.method, self.crypto = ex_type, method, crypto
        cfg = EX_TYPES[ex_type]

        self.amount = discord.ui.TextInput(
            label=f"Exchange amount ({cfg['unit']})", placeholder="e.g. 1000", max_length=12
        )
        payout_label = {
            "inr_to_crypto": "Your wallet address (to receive crypto)",
            "crypto_to_inr": "Your UPI ID / bank details (to receive INR)",
            "crypto_to_crypto": "Your wallet address (to receive crypto)",
        }[ex_type]
        self.payout = discord.ui.TextInput(
            label=payout_label, style=discord.TextStyle.paragraph, max_length=300
        )
        self.add_item(self.amount)
        self.add_item(self.payout)

    async def on_submit(self, interaction: discord.Interaction):
        # Defer immediately: rates + channel creation can take longer than 3 seconds
        await interaction.response.defer(ephemeral=True, thinking=True)
        cfg = EX_TYPES[self.ex_type]

        # --- validate the amount
        try:
            amount = float(self.amount.value.replace(",", "").strip())
        except ValueError:
            return await interaction.followup.send("Amount must be a number.", ephemeral=True)
        if not math.isfinite(amount) or amount <= 0:
            return await interaction.followup.send("Enter a valid positive amount.", ephemeral=True)
        if amount < cfg["min"]:
            return await interaction.followup.send(
                f"Minimum for this exchange is {cfg['min']} {cfg['unit']}.", ephemeral=True
            )

        # --- calculate
        try:
            calc = await calculate(self.ex_type, amount, self.method, self.crypto, cfg["fee"])
        except Exception:
            return await interaction.followup.send(
                "Could not fetch live rates right now. Please try again in a minute.", ephemeral=True
            )

        # --- create DB row first (to get the ticket number), then the channel
        payout = self.payout.value.strip()
        ticket_id = await db.insert(
            "INSERT INTO tickets (guild_id, channel_id, user_id, kind, ex_type, method, crypto, "
            "amount, fee, receive_amount, rate, payout_details, volume_inr) "
            "VALUES (?, 0, ?, 'exchange', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (interaction.guild_id, interaction.user.id, self.ex_type, self.method, self.crypto,
             amount, calc["fee"], calc["receive"], calc["rate"], payout, calc["volume_inr"]),
        )

        try:
            channel = await tickets.create_ticket_channel(
                interaction.guild, interaction.user,
                name=f"{cfg['slug']}-{ticket_id:04d}",
                topic=f"Exchange ticket #{ticket_id} for {interaction.user}",
            )
        except discord.HTTPException:
            await db.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
            return await interaction.followup.send(
                "I could not create the ticket channel. Ask an admin to check my permissions.",
                ephemeral=True,
            )

        await db.execute("UPDATE tickets SET channel_id=? WHERE id=?", (channel.id, ticket_id))

        # --- ticket message
        embed = discord.Embed(title=f"{BRAND} - Transaction Details", color=EMBED_COLOR)
        embed.add_field(name="Ticket", value=f"#{ticket_id:04d}")
        embed.add_field(name="Customer", value=interaction.user.mention)
        embed.add_field(name="Type", value=cfg["label"])
        embed.add_field(name="You send", value=calc["send_text"], inline=False)
        embed.add_field(name="Fee", value=calc["fee_text"])
        embed.add_field(name="You receive", value=calc["receive_text"])
        embed.add_field(name="Rate used", value=calc["rate_text"], inline=False)
        embed.add_field(name="Payout details", value=f"```{payout.replace('`', chr(39))}```", inline=False)
        embed.set_footer(text="Rates are estimates. Staff will confirm the final amount before you pay.")

        staff_role_id = await db.get_setting(interaction.guild_id, "staff_role")
        ping = f"<@&{staff_role_id}> " if staff_role_id else ""
        await channel.send(
            content=f"{ping}{interaction.user.mention}",
            embed=embed, view=ExchangeTicketView(), allowed_mentions=MENTIONS,
        )
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


# ---------------------------------------------------- ticket buttons (persistent)
class ExchangeTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", emoji="✅", style=discord.ButtonStyle.success,
                       custom_id="exchange:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await tickets.claim_ticket(interaction):
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.channel.send(f"✅ Ticket claimed by {interaction.user.mention}.")

    @discord.ui.button(label="Complete Deal", emoji="💰", style=discord.ButtonStyle.primary,
                       custom_id="exchange:complete")
    async def complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_staff(interaction):
            return await interaction.response.send_message("Staff only.", ephemeral=True)

        ticket = await tickets.get_ticket(interaction.channel_id)
        if not ticket:
            return await interaction.response.send_message("Ticket not found.", ephemeral=True)

        is_admin = interaction.user.guild_permissions.administrator
        if ticket["claimed_by"] != interaction.user.id and not is_admin:
            return await interaction.response.send_message(
                "Only the staff member who claimed this ticket can complete it.", ephemeral=True
            )

        changed = await db.execute(
            "UPDATE tickets SET completed=1 WHERE channel_id=? AND completed=0",
            (interaction.channel_id,),
        )
        if not changed:
            return await interaction.response.send_message("Already marked complete.", ephemeral=True)

        # Post the "Deal Logged" embed
        cfg = EX_TYPES[ticket["ex_type"]]
        log = discord.Embed(title="Deal Logged", color=0x57F287)
        log.add_field(name="Ticket", value=f"#{ticket['id']:04d}")
        log.add_field(name="Customer", value=f"<@{ticket['user_id']}>")
        log.add_field(name="Handled by", value=interaction.user.mention)
        log.add_field(name="Type", value=cfg["label"])
        log.add_field(name="Amount", value=f"{ticket['amount']:,.2f} {cfg['unit']}")
        log.add_field(name="Fee", value=f"{ticket['fee']:,.2f} {cfg['unit']}")
        log.add_field(name="Method / Coin", value=f"{ticket['method']} / {ticket['crypto']}")

        log_id = await db.get_setting(interaction.guild_id, "deal_log_channel")
        if log_id:
            channel = interaction.guild.get_channel(int(log_id))
            if channel:
                await channel.send(embed=log)

        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send("💰 Deal marked as **completed**. You can now close the ticket.")

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger,
                       custom_id="exchange:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.prompt_close(interaction)


# ------------------------------------------------------------------------ cog
class ExchangeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Re-register persistent views so buttons survive restarts
        self.bot.add_view(ExchangePanelView())
        self.bot.add_view(ExchangeTicketView())

    @app_commands.command(name="exchange_panel", description="Post the exchange panel in this channel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def exchange_panel(self, interaction: discord.Interaction):
        await interaction.channel.send(embed=panel_embed(), view=ExchangePanelView())
        await interaction.response.send_message("Panel posted.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ExchangeCog(bot))
```

### How this file works, piece by piece

1. **`panel_embed()`** builds the public message with fees and minimums (read from `config.py`, so you edit one place).
2. **`ExchangeTypeSelect`** is the main dropdown. Its fixed `custom_id` and the panel's `timeout=None` make it persistent. After responding, the code re-edits the panel message so the dropdown resets (otherwise users could not pick the same option twice).
3. **`OptionsView`** is an ephemeral view with two dropdowns whose labels change per exchange type, plus **Continue**. Choices are stored on the view object.
4. **`DetailsModal`** is the form. `on_submit` first calls `defer()` (so Discord doesn't time out), validates input (number, finite, positive, above minimum), calculates amounts, saves a database row, creates the private channel and posts the transaction embed with buttons.
5. **`ExchangeTicketView`** has Claim, Complete Deal, Close. Claim uses an atomic SQL update, so two staff clicking at once can't both claim. Complete Deal can only be pressed by the claiming staff member (or an admin), flags the ticket as completed and posts the deal log. Close asks for confirmation, then saves the transcript and deletes the channel.

---

## Part 12: Stats cog

Create `cogs/stats.py`:

```python
# cogs/stats.py
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
```

The f-string SQL here is safe because `column` only ever comes from two hardcoded values, never from user input. **Never** put user input into SQL with f-strings; always use `?` placeholders as the rest of the code does.

---

## Part 13: Support and applications cog

Create `cogs/support.py`. It adds a support ticket panel and a staff application panel with Accept/Deny buttons.

```python
# cogs/support.py
import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import BRAND, EMBED_COLOR
from utils import tickets
from utils.checks import is_staff


# ============================================================ SUPPORT TICKETS
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


# ========================================================= STAFF APPLICATIONS
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
        embed.set_footer(text=f"Applicant ID: {interaction.user.id}")   # used by the buttons below

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
        await self._decide(interaction, False)


# ================================================================== COG
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
```

---

## Part 14: Discord server setup

Create this structure in your server (names are up to you):

```
📁 EXCHANGE            ← category: put exchange_panel + support_panel channels here
   #exchange           ← public: exchange panel
   #support            ← public: support panel
   #apply              ← public: application panel
📁 TICKETS             ← category: bot creates ticket channels here
📁 STAFF ONLY
   #deal-logs          ← only staff can see
   #transcripts        ← only staff can see
   #applications       ← only staff can see
```

Also create a **Staff** role.

**Critical permission rule:** the bot's role must have **View Channel, Send Messages, Read Message History, Attach Files, Embed Links** (server-wide or in the TICKETS category), because a bot can only grant permissions to others that it has itself. Also move the bot's role **above** the Staff role in Server Settings → Roles.

---

## Part 15: Run and test

### 15.1 Start the bot

```bash
python bot.py
```

You should see `Logged in as ...`. If the console shows errors, jump to Part 19.

### 15.2 Configure it

In your server run:

```
/setup staff_role:@Staff ticket_category:TICKETS deal_log_channel:#deal-logs transcript_channel:#transcripts applications_channel:#applications
```

### 15.3 Post the panels

- In `#exchange` run `/exchange_panel`
- In `#support` run `/support_panel`
- In `#apply` run `/apply_panel`

### 15.4 Test checklist

Use a second Discord account (or ask a friend) as the customer.

| # | Test | Expected result |
|---|---|---|
| 1 | Pick **INR to Crypto** | Ephemeral picker appears with two dropdowns |
| 2 | Press Continue without choosing | "Please choose both options first." |
| 3 | Choose UPI + USDT, Continue | Form opens |
| 4 | Type `abc` as the amount | "Amount must be a number." |
| 5 | Type `10` | Minimum error |
| 6 | Type `1000` + a wallet address | Ticket channel created, embed with fee and receive amount |
| 7 | Pick an exchange type again | "You already have an open ticket" |
| 8 | Customer presses **Claim** | "Only staff can claim tickets." |
| 9 | Staff presses **Claim** | Button disables, claim message appears |
| 10 | A different staff member presses **Complete Deal** | Refused (only the claimer can) |
| 11 | Claimer presses **Complete Deal** | Deal Logged embed in `#deal-logs` |
| 12 | Press **Close** → confirm | Transcript in `#transcripts`, DM to user, channel deleted after 5 s |
| 13 | `/leaderboard` and `/profile` | The deal shows up |
| 14 | **Restart the bot**, press panel dropdown and ticket buttons | Everything still works (persistent views) |
| 15 | Try Crypto to Crypto with the same coin both sides | Refused |

---

## Part 16: Deploy 24/7

Your bot only runs while the script runs. Options:

| Option | Notes |
|---|---|
| **VPS** (Hetzner, DigitalOcean, Contabo, Oracle free tier) | Best control, ~₹300+/month |
| **Railway / Fly.io / Render** | Easy deploys. You need a persistent volume for `exchange.db`, otherwise data is lost on redeploy |
| **Home PC / Raspberry Pi** | Free, but goes down when power or internet does |

### VPS with systemd (Ubuntu)

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
git clone <your-private-repo> exchange-bot    # or upload the folder
cd exchange-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nano .env                                      # add DISCORD_TOKEN (leave DEV_GUILD_ID out in production)
```

Create `/etc/systemd/system/exchange-bot.service`:

```ini
[Unit]
Description=Discord Exchange Bot
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/exchange-bot
ExecStart=/home/ubuntu/exchange-bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now exchange-bot
sudo systemctl status exchange-bot
journalctl -u exchange-bot -f      # live logs
```

**Back up `exchange.db` regularly** (for example a daily cron job copying it elsewhere). It holds all your deal history.

---

## Part 17: Security, scam protection, legal

### Bot security

- **Never commit `.env`.** If the token leaks, click Reset Token in the Developer Portal immediately.
- Give the bot only the permissions listed in Part 4, **not Administrator**.
- All staff actions check `is_staff()`. Keep it that way for any new button you add.
- Always use `?` placeholders in SQL. Never build queries from user input.
- Keep your server and VPS accounts protected with 2FA.

### Operational rules for your staff (strongly recommended)

P2P exchange servers are a common target for scammers and chargeback fraud. Put these in your server rules:

- Staff **never** move funds outside the ticket channel, and never via DMs.
- Only accept payment **from an account in the customer's own name**; refuse third-party payments.
- Confirm that funds have **actually settled** in your account before releasing crypto. Screenshots can be faked.
- Crypto transfers are irreversible, so double-check addresses and networks (for example USDT on TRC20 vs BEP20) before sending.
- Start with low limits for new customers and raise them with history.
- Keep every transcript. They are your evidence in a dispute.
- Staff should never share private keys, seed phrases or login codes.

### Legal and platform note

Running an exchange service may bring legal obligations depending on your country: AML/KYC rules, registration, and taxes. In India, for example, virtual digital asset businesses face compliance and tax requirements. Also check Discord's policies on what services may be offered through servers. This guide is technical help, not legal advice, so talk to a qualified professional before operating commercially.

---

## Part 18: Optional upgrades

Build these once the base bot works.

1. **Editable fees and rates from Discord**
   Store `fee_<type>` in the `settings` table and add `/setfee` and `/setrate` admin commands, instead of editing `config.py`.

2. **Manual fixed rates**
   Many exchanges quote their own USDT/INR rate. Add a `usdt_inr_rate` setting and have `calc.py` use it when present, instead of CoinGecko.

3. **Network selection (TRC20 / BEP20 / ERC20)**
   Add a third dropdown to `OptionsView` and include the network in the embed.

4. **Automatic blockchain verification** (advanced)
   After the customer pastes a transaction hash, query a chain explorer API (for example TronGrid for TRON, Blockcypher or Blockchair for BTC/LTC, Etherscan for Ethereum) and check: correct destination address, correct token, amount at least the expected amount, and enough confirmations. Show a "Verified ✅" status in the ticket. Treat API results as a helper, not as the only check, and make staff confirm.

5. **Ticket inactivity auto-close**
   Use `discord.ext.tasks` to scan for tickets with no messages for 24 hours and warn then close them.

6. **Blacklist**
   A `blacklist` table checked at the start of `ExchangeTypeSelect.callback`.

7. **Daily and weekly volume reports**
   A scheduled task posting totals to `#deal-logs`.

8. **Web dashboard**
   Expose stats with FastAPI plus a simple front-end.

---

## Part 19: Troubleshooting

| Problem | Cause and fix |
|---|---|
| `discord.errors.LoginFailure: Improper token` | Wrong or missing `DISCORD_TOKEN`. Reset the token, update `.env`. |
| `PrivilegedIntentsRequired` | Enable **Message Content Intent** in the Developer Portal → Bot. |
| Slash commands don't appear | Set `DEV_GUILD_ID` for instant sync. Global sync can take a while. Check that the bot was invited with the `applications.commands` scope. Restart Discord (Ctrl+R). |
| "This interaction failed" | You took longer than 3 seconds to respond. Call `await interaction.response.defer()` first for slow work. |
| Buttons stop working after restart | The view is missing `timeout=None`, a `custom_id`, or the `bot.add_view(...)` call in `cog_load`. |
| "I could not create the ticket channel" | The bot lacks **Manage Channels**, or lacks a permission it tries to grant, or the ticket category is full (50 channel limit per category). |
| Transcript messages are empty | Message Content Intent is off in code or in the portal. |
| Staff role is not pinged | The role is not mentionable and the bot lacks **Mention Everyone**. Enable one of them. |
| Rates fail ("Could not fetch live rates") | CoinGecko rate limit or network issue. Wait a minute, or add a manual fallback rate (Part 18, item 2). |
| `ModuleNotFoundError: No module named 'utils'` | Run `python bot.py` from the `exchange-bot` folder, and make sure `utils/__init__.py` exists. |
| `sqlite3.OperationalError: no such column` | You changed the schema after the DB was created. Delete `exchange.db` during development (this erases data), or add the column with `ALTER TABLE`. |
| Dropdown shows the old choice selected | Make sure the panel message edit at the end of `ExchangeTypeSelect.callback` is present. |
| Two staff claim the same ticket | Make sure you kept the `claimed_by IS NULL` condition in the claim SQL. |

---

## Final checklist before going live

- [ ] Tested every flow on a **test server** first
- [ ] Token only in `.env`, `.env` in `.gitignore`
- [ ] Bot has minimum permissions, not Administrator
- [ ] `/setup` completed; staff role works
- [ ] Panels posted in public channels; logs and transcripts channels are staff-only
- [ ] Staff rules written and shared (Part 17)
- [ ] `exchange.db` backup scheduled
- [ ] Bot running under systemd (or another host) with auto-restart
- [ ] You have checked local legal requirements

Good luck. If something breaks, copy the exact error from the console and look it up in Part 19 first.
