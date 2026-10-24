# Discord Exchange Ticket Bot, Version 2 (Crix-style UI + Comma Commands)

Full step-by-step guide. This replaces v1. It includes every file, complete code, setup, commands, testing and troubleshooting.

---

## What is new in v2

| # | Change | Where |
|---|---|---|
| 1 | **`,` prefix commands** (hybrid: `,lb` and `/lb` both work) with the full command list from your reference bot | Parts 10 and 13 |
| 2 | **Panel UI rebuilt** to match the reference: small brand line, logo on the right, big "SECURE EXCHANGE SERVICE", fixed rates (`104 / $`, `102 / $`), dropdown | Part 11.3 |
| 3 | **Ticket UI rebuilt** to match the reference: role pings, "Transaction Details" with code-style fields, footer, buttons **Claim / Req MM / Close** | Part 11.5 |
| 4 | **Fixed rates** per dollar (set with `,setrate`) instead of live CoinGecko prices and percentage fees | Part 8.3 |
| 5 | **Picker message auto-deletes** after the ticket is created (and when it times out) | Part 11.4 |
| 6 | **Separate roles per ticket type**: Exchanger roles for exchange tickets, Support roles for support tickets, Owner/Founder for staff-application tickets, Middleman roles, Manager roles | Parts 8.1, 10.1 |
| 7 | **Staff applications are now tickets** (private channel, only Owner/Founder can see and claim) | Part 10.3 |
| 8 | Channel renames to `claimed-<staffname>` on claim and back on unclaim | Part 8.4 |
| 9 | Leaderboards, profiles, vouches, tax and staff fees, manual leaderboard edits | Part 10.5 |

### Read this first: what is copied and what is my interpretation

- **Copied from your screenshots (layout and text):** panel layout, ticket layout, button names, field names, footer format, the `claimed-name` rename, the picker with two dropdowns plus Continue.
- **My interpretation (marked ⚠️):** your command list came from a one-line description of each command, and I never saw the original bot's code. I built each command to match its description in the most sensible way. If one behaves differently from your reference bot, tell me what it should do and it is a small edit.
- **Your own branding:** the reference bot's logo and name belong to its owner. Use **your own** brand name and logo (Part 5).

---

## Table of Contents

1. [How the system works](#part-1-how-the-system-works)
2. [Prerequisites](#part-2-prerequisites)
3. [Create and invite the bot](#part-3-create-and-invite-the-bot)
4. [Project setup](#part-4-project-setup)
5. [Logo asset](#part-5-logo-asset)
6. [config.py](#part-6-configpy)
7. [database.py](#part-7-databasepy)
8. [Utility modules](#part-8-utility-modules)
9. [bot.py](#part-9-botpy)
10. [Cogs](#part-10-cogs)
11. [UI mapping: screenshot to code](#part-11-ui-mapping)
12. [Discord server layout](#part-12-discord-server-layout)
13. [First-time configuration](#part-13-first-time-configuration)
14. [Command reference](#part-14-command-reference)
15. [Testing checklist](#part-15-testing-checklist)
16. [Hosting](#part-16-hosting)
17. [Security, scams, legal](#part-17-security-scams-legal)
18. [Customization recipes](#part-18-customization-recipes)
19. [Troubleshooting](#part-19-troubleshooting)
20. [Final checklist](#part-20-final-checklist)

---

## Part 1: How the system works

### User flow

```
#exchange panel (dropdown)
  └─ user picks "INR to Crypto" or "Crypto to INR"
      └─ private picker: [what you SEND] [what you RECEIVE] [Continue]
          └─ Continue opens a small form: amount in USD
              └─ bot calculates with your FIXED rate
                  └─ private ticket channel + role pings
                      └─ the picker message deletes itself
                          └─ staff: Claim → handle → Close → "Deal completed & close"
                              └─ transcript, deal log, stats, tax recorded
```

### Who can do what (roles)

| Role kind (`,addrole <kind> @role`) | Example roles | Can |
|---|---|---|
| `exchanger` | Senior Exchanger, Junior Exchanger | See, claim, complete **exchange** tickets |
| `support` | Support Staff | See and claim **support** tickets |
| `application` | Owner, Founder | See, claim, accept/deny **staff application** tickets |
| `middleman` | Middleman | Added to a ticket when someone presses **Req MM** |
| `manager` | Owner, Founder | Admin-style commands: rates, tax, leaderboard edits, panels, override claims |

Server administrators always pass every check. One role can have several kinds (for example Owner can be `application` and `manager`).

### Project architecture

| File | Purpose |
|---|---|
| `bot.py` | Starts the bot, loads cogs, syncs slash commands, handles command errors |
| `config.py` | Brand, prefix, timezone, coins, payment methods, defaults |
| `database.py` | SQLite tables and helpers |
| `utils/checks.py` | Role checks, `require()` decorator, `SafeModal` |
| `utils/calc.py` | Fixed-rate calculation |
| `utils/transcript.py` | HTML transcript |
| `utils/tickets.py` | Ticket logic: create, claim, unclaim, Req MM, close, complete deal |
| `utils/ticket_views.py` | The button rows inside tickets (persistent views) |
| `utils/confirm.py` | Reusable confirm/cancel buttons |
| `cogs/setup_cog.py` | `,setup`, `,addrole`, `,removerole`, `,roles`, `,setrate`, `,setfee`, `,settax` |
| `cogs/exchange.py` | Exchange panel, pickers, form, ticket creation |
| `cogs/support.py` | Support panel and staff application panel |
| `cogs/ticket_commands.py` | `,claim` `,uc` `,v` `,3p` `,close` `,transcript` |
| `cogs/stats.py` | `,p` `,lb` `,clb` `,deals` `,e` `,mytax` `,stafffees` `,cleartax` `,addlb` `,setlb` `,resetlb` |
| `cogs/calculators.py` | `,i2c` `,c2i` `,c2c` `,cr2i` `,cr2c` `,c2cr` `,rates` `,help` |

### Concepts

- **Cog**: a class that groups commands and listeners.
- **Hybrid command**: one function that works as both `,command` and `/command`.
- **View**: buttons or dropdowns attached to a message. **Persistent view**: `timeout=None` plus fixed `custom_id`s, re-registered at startup so buttons survive restarts.
- **Modal**: a popup form. **Ephemeral**: visible only to one user.
- Interactions must be answered within **3 seconds**; slower work starts with `defer()`.

---

## Part 2: Prerequisites

1. **Python 3.10+** (`python --version`).
2. A Discord account and a **test server** where you are admin.
3. Discord **Developer Mode** on (User Settings → Advanced) to copy IDs.
4. A code editor (VS Code, or `nano` on your Linux box).

---

## Part 3: Create and invite the bot

### 3.1 Create the application

1. Open <https://discord.com/developers/applications> → **New Application**.
2. **Bot** tab → **Reset Token** → copy the token. Never share it.
3. **Privileged Gateway Intents**: turn on **Message Content Intent** (needed for `,` commands and transcripts).
4. Turn **Public Bot** off. Save.
5. Optional: set the bot's name and avatar here.

### 3.2 Invite it

**OAuth2 → URL Generator**

- Scopes: `bot`, `applications.commands`
- Bot permissions (do **not** tick Administrator):
  - View Channels
  - Manage Channels
  - Manage Roles (needed so the bot can add people with `,3p` and add middleman roles on **Req MM**)
  - Send Messages
  - Embed Links
  - Attach Files
  - Read Message History
  - Mention Everyone (so role pings work)
  - Manage Messages (optional: lets it delete your `,panel` command message)

Open the URL, choose your test server, Authorize.

---

## Part 4: Project setup

### 4.1 Folder and virtual environment

```bash
cd /home/mrrobot/Projects/assistance      # or any folder you like
python -m venv venv
source venv/bin/activate                   # Windows: venv\Scripts\Activate.ps1
```

### 4.2 Structure

```
assistance/
├── .env
├── .gitignore
├── requirements.txt
├── bot.py
├── config.py
├── database.py
├── assets/
│   └── logo.png            ← your logo (Part 5)
├── utils/
│   ├── __init__.py
│   ├── checks.py
│   ├── calc.py
│   ├── transcript.py
│   ├── tickets.py
│   ├── ticket_views.py
│   └── confirm.py
└── cogs/
    ├── __init__.py
    ├── setup_cog.py
    ├── exchange.py
    ├── support.py
    ├── ticket_commands.py
    ├── stats.py
    └── calculators.py
```

```bash
mkdir -p utils cogs assets
touch utils/__init__.py cogs/__init__.py
```

You can delete v1's `utils/rates.py` and `cogs/stats.py` content; they are replaced below.

### 4.3 `requirements.txt`

```
discord.py>=2.4
python-dotenv>=1.0
aiosqlite>=0.20
tzdata
```

```bash
pip install -r requirements.txt
```

### 4.4 `.env`

```
DISCORD_TOKEN=paste_your_token_here
DEV_GUILD_ID=paste_your_test_server_id_here
```

### 4.5 `.gitignore`

```
.env
venv/
__pycache__/
*.db
```

### 4.6 If you ran v1 before

The database layout changed. **Delete the old `exchange.db`** (test data only):

```bash
rm -f exchange.db
```

---

## Part 5: Logo asset

The panel shows a logo on the right side. Put **your own** square image (PNG, 512×512 recommended) here:

```
assets/logo.png
```

The bot attaches it to the panel message and references it as `attachment://logo.png`, so it never expires (unlike pasted Discord image links). If the file is missing, the panel simply has no logo.

---

## Part 6: `config.py`

Everything you may want to change lives here.

```python
# config.py

PREFIX = ","                       # command prefix
BRAND = "Your Exchange"            # shown on panel and ticket titles (use your own brand)
EMBED_COLOR = 0x2B2D31             # dark embed bar like the reference
LOGO_PATH = "assets/logo.png"
TIMEZONE = "Asia/Kolkata"          # used for the ticket footer time

PANEL_AMOUNT_TEXT = "Any amount"   # text on the panel before the rate
MIN_USD = 1.0                      # smallest allowed amount in USD (set 0.01 for "any amount")

# Defaults. Change them live with  ,setrate  ,setfee  ,settax
DEFAULT_RATES = {
    "inr_to_crypto": 104.0,        # you pay 104 INR for each $1 of crypto
    "crypto_to_inr": 102.0,        # you receive 102 INR for each $1 of crypto
}
DEFAULT_C2C_FEE = 3.0              # percent, only used if crypto_to_crypto is enabled
DEFAULT_TAX_PERCENT = 1.0          # percent of deal volume recorded as staff tax (my assumption, edit freely)

EX_TYPES = {
    "inr_to_crypto": {
        "label": "INR to Crypto",
        "panel_title": "INR → CRYPTO",
        "category": "INR 2 Crypto",
        "slug": "inr-crypto",
        "enabled": True,
    },
    "crypto_to_inr": {
        "label": "Crypto to INR",
        "panel_title": "CRYPTO → INR",
        "category": "Crypto 2 INR",
        "slug": "crypto-inr",
        "enabled": True,
    },
    "crypto_to_crypto": {
        "label": "Crypto to Crypto",
        "panel_title": "CRYPTO → CRYPTO",
        "category": "Crypto 2 Crypto",
        "slug": "crypto-crypto",
        "enabled": False,          # the reference panel only has two types; set True to add this one
    },
}

# label shown in the dropdown : short code shown in the ticket (e.g. GPAY)
INR_METHODS = {
    "UPI": "UPI",
    "Bank Transfer": "BANK",
    "IMPS": "IMPS",
    "Google Pay": "GPAY",
    "PhonePe": "PHONEPE",
    "Paytm": "PAYTM",
    "Fampay": "FAMPAY",
    "Omnicard": "OMNICARD",
    "Mobikwik": "MOBIKWIK",
}

CRYPTOS = ["USDT", "BTC", "LTC", "ETH", "SOL", "TRX", "BNB"]

ROLE_KINDS = {
    "exchanger": "Can see, claim and complete exchange tickets",
    "support": "Can see and claim support tickets",
    "application": "Can see, claim, accept or deny staff application tickets",
    "middleman": "Gets added to a ticket when Req MM is pressed",
    "manager": "Can use admin commands (rates, tax, leaderboard edits, panels)",
}

# Used by ,v   Available keys: {staff} {category} {amount} {exchange}
VOUCH_FORMAT = "+rep {staff} | {category} | ${amount:.2f} | {exchange} | Smooth and fast exchange"
```

**How the amount works (matches the reference ticket):**

| Type | User enters | Auto Calculation |
|---|---|---|
| INR to Crypto | USD amount of crypto they want | `Rs.<usd × inr_to_crypto rate> INR needs to be paid` |
| Crypto to INR | USD value of the crypto they send | `Rs.<usd × crypto_to_inr rate> INR will be received` (so $5 × 102 = Rs.510.00) |
| Crypto to Crypto | USD value they send | `$<usd minus fee> <coin> will be received (fee %)` |

---

## Part 7: `database.py`

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

CREATE TABLE IF NOT EXISTS role_perms (
    guild_id INTEGER NOT NULL,
    kind     TEXT NOT NULL,
    role_id  INTEGER NOT NULL,
    PRIMARY KEY (guild_id, kind, role_id)
);

CREATE TABLE IF NOT EXISTS tickets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      INTEGER NOT NULL,
    channel_id    INTEGER NOT NULL,
    message_id    INTEGER,
    base_name     TEXT,
    user_id       INTEGER NOT NULL,
    kind          TEXT NOT NULL,                 -- exchange | support | apply
    ex_type       TEXT,
    send_asset    TEXT,
    recv_asset    TEXT,
    amount_usd    REAL,
    inr_amount    REAL,
    rate          REAL,
    fee_usd       REAL DEFAULT 0,
    calc_text     TEXT,
    claimed_by    INTEGER,
    mm_requested  INTEGER NOT NULL DEFAULT 0,
    decision      TEXT,                          -- accepted | denied (apply tickets)
    status        TEXT NOT NULL DEFAULT 'open',  -- open | closed
    completed     INTEGER NOT NULL DEFAULT 0,    -- 1 = deal finished
    tax_usd       REAL NOT NULL DEFAULT 0,
    tax_cleared   INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at  TEXT,
    closed_at     TEXT
);

CREATE TABLE IF NOT EXISTS vouches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    given_by   INTEGER NOT NULL,
    note       TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS manual_stats (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    deals      INTEGER NOT NULL DEFAULT 0,
    volume_usd REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tickets_channel ON tickets(channel_id);
CREATE INDEX IF NOT EXISTS idx_tickets_user    ON tickets(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_claimed ON tickets(guild_id, claimed_by);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def insert(query, params=()):
    """INSERT and return the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        await db.commit()
        return cur.lastrowid


async def execute(query, params=()):
    """UPDATE/DELETE and return the number of rows changed."""
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
    row = await fetchone("SELECT value FROM settings WHERE guild_id=? AND key=?", (guild_id, key))
    return row["value"] if row else None


async def set_setting(guild_id, key, value):
    await execute(
        "INSERT INTO settings (guild_id, key, value) VALUES (?, ?, ?) "
        "ON CONFLICT(guild_id, key) DO UPDATE SET value=excluded.value",
        (guild_id, key, str(value)),
    )
```

---

## Part 8: Utility modules

### 8.1 `utils/checks.py`: roles and permission helpers

```python
# utils/checks.py
import traceback
import discord
from discord.ext import commands
import database as db


async def role_ids_for(guild_id: int, *kinds: str) -> list[int]:
    """Role IDs configured for any of the given kinds."""
    marks = ",".join("?" for _ in kinds)   # only '?' characters are inserted, never user input
    rows = await db.fetchall(
        f"SELECT DISTINCT role_id FROM role_perms WHERE guild_id=? AND kind IN ({marks})",
        (guild_id, *kinds),
    )
    return [r["role_id"] for r in rows]


async def member_has_kind(member, *kinds: str) -> bool:
    """True for server admins, or members holding a role configured for any of these kinds."""
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    ids = set(await role_ids_for(member.guild.id, *kinds))
    return any(r.id in ids for r in member.roles)


def require(*kinds: str):
    """Command decorator: only allow members with one of these role kinds (admins always pass)."""
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        if await member_has_kind(ctx.author, *kinds):
            return True
        raise commands.CheckFailure("You don't have permission to use this command.")
    return commands.check(predicate)


class SafeModal(discord.ui.Modal):
    """Modal that reports errors to the user instead of failing silently."""
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        traceback.print_exception(type(error), error, error.__traceback__)
        msg = "Something went wrong. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
```

### 8.2 `utils/confirm.py`: confirm buttons

```python
# utils/confirm.py
import discord


class ConfirmView(discord.ui.View):
    """Confirm / Cancel buttons that only the command author can press."""
    def __init__(self, user_id: int, on_confirm, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.on_confirm = on_confirm      # async function(interaction)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Working...", view=None)
        await self.on_confirm(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", view=None)
```

### 8.3 `utils/calc.py`: fixed-rate calculation

```python
# utils/calc.py
import database as db
from config import DEFAULT_RATES, DEFAULT_C2C_FEE, DEFAULT_TAX_PERCENT


async def _num(guild_id: int, key: str, default: float) -> float:
    value = await db.get_setting(guild_id, key)
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


async def get_rate(guild_id: int, ex_type: str) -> float:
    return await _num(guild_id, f"rate_{ex_type}", DEFAULT_RATES[ex_type])


async def get_c2c_fee(guild_id: int) -> float:
    return await _num(guild_id, "fee_crypto_to_crypto", DEFAULT_C2C_FEE)


async def get_tax_percent(guild_id: int) -> float:
    return await _num(guild_id, "tax_percent", DEFAULT_TAX_PERCENT)


async def calculate(guild_id: int, ex_type: str, amount_usd: float, send: str, recv: str) -> dict:
    """Returns rate, inr_amount, fee_usd and the 'Auto Calculation' text for the ticket."""
    if ex_type == "inr_to_crypto":
        rate = await get_rate(guild_id, ex_type)
        inr = round(amount_usd * rate, 2)
        return {"rate": rate, "inr_amount": inr, "fee_usd": 0.0,
                "calc_text": f"Rs.{inr:,.2f} INR needs to be paid"}

    if ex_type == "crypto_to_inr":
        rate = await get_rate(guild_id, ex_type)
        inr = round(amount_usd * rate, 2)
        return {"rate": rate, "inr_amount": inr, "fee_usd": 0.0,
                "calc_text": f"Rs.{inr:,.2f} INR will be received"}

    # crypto_to_crypto
    fee_pct = await get_c2c_fee(guild_id)
    fee = round(amount_usd * fee_pct / 100, 4)
    net = amount_usd - fee
    return {"rate": fee_pct, "inr_amount": 0.0, "fee_usd": fee,
            "calc_text": f"${net:,.2f} {recv} will be received ({fee_pct:g}% fee)"}
```

### 8.4 `utils/transcript.py`

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
            extras.append(f'<div class="att">📎 <a href="{html.escape(a.url)}">{html.escape(a.filename)}</a></div>')

        for e in m.embeds:
            parts = []
            if e.title:
                parts.append(f"<b>{html.escape(e.title)}</b>")
            if e.description:
                parts.append(html.escape(e.description).replace("\n", "<br>"))
            for f in e.fields:
                parts.append(f"<b>{html.escape(f.name)}:</b> {html.escape(f.value).replace(chr(10), '<br>')}")
            extras.append('<div class="embed">' + "<br>".join(parts) + "</div>")

        rows.append(
            f'<div class="msg"><div class="meta"><b>{author}</b> <span class="ts">{ts}</span></div>'
            f'<div>{body}</div>{"".join(extras)}</div>'
        )

    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Transcript - {html.escape(channel.name)}</title>
<style>
body {{ background:#313338; color:#dbdee1; font-family:Arial,sans-serif; padding:20px; }}
.msg {{ padding:8px 0; border-bottom:1px solid #3f4147; }}
.ts {{ color:#949ba4; font-size:12px; margin-left:8px; }}
.embed {{ border-left:4px solid #5865F2; background:#2b2d31; padding:8px; margin-top:4px; }}
.att a {{ color:#00a8fc; }}
</style></head><body>
<h2>#{html.escape(channel.name)}</h2><p>{len(rows)} messages</p>
{"".join(rows)}
</body></html>"""
    return page.encode("utf-8")
```

### 8.5 `utils/tickets.py`: the ticket engine

All ticket behaviour lives here, shared by buttons and `,` commands.

```python
# utils/tickets.py
import asyncio
import io
import re
import discord
import database as db
from config import EMBED_COLOR, EX_TYPES
from utils.checks import member_has_kind, role_ids_for
from utils.transcript import build_transcript
from utils.calc import get_tax_percent

# which role kind handles which ticket kind
KIND_ROLE = {"exchange": "exchanger", "support": "support", "apply": "application"}

# role/user pings are allowed only where we explicitly pass this
PINGS = discord.AllowedMentions(roles=True, users=True, everyone=False)


# ------------------------------------------------------------------ basics
async def get_ticket(channel_id: int):
    return await db.fetchone("SELECT * FROM tickets WHERE channel_id=?", (channel_id,))


async def existing_open(guild_id: int, user_id: int, kind: str):
    return await db.fetchone(
        "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? AND kind=? AND status='open'",
        (guild_id, user_id, kind),
    )


async def staff_pings(guild: discord.Guild, kind: str) -> str:
    ids = await role_ids_for(guild.id, KIND_ROLE[kind])
    return " ".join(f"<@&{i}>" for i in ids)


def clean_name(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", text.lower())[:40] or "staff"


async def rename_channel(channel: discord.TextChannel, name: str):
    """Renames can be rate-limited (2 per 10 min), so failures are ignored."""
    try:
        await channel.edit(name=name)
    except discord.HTTPException:
        pass


# ------------------------------------------------------------ create ticket
async def create_ticket_channel(guild, member, name, kind, topic=None) -> discord.TextChannel:
    """Private channel for: the member, the roles for this ticket kind, manager roles, and the bot."""
    base = dict(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(**base),
        guild.me: discord.PermissionOverwrite(**base, embed_links=True, manage_channels=True),
    }
    for rid in await role_ids_for(guild.id, KIND_ROLE[kind], "manager"):
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(**base)

    category = None
    category_id = await db.get_setting(guild.id, "ticket_category")
    if category_id:
        found = guild.get_channel(int(category_id))
        if isinstance(found, discord.CategoryChannel):
            category = found

    return await guild.create_text_channel(name=name, overwrites=overwrites, category=category, topic=topic)


async def new_ticket(guild, member, kind: str, slug: str, fields: dict):
    """
    1) insert a DB row (to get the ticket number)
    2) create the channel named <slug>-<0000>
    3) store the channel id
    Returns (ticket_id, channel). Raises discord.HTTPException if the channel cannot be created.
    """
    cols = {"guild_id": guild.id, "channel_id": 0, "user_id": member.id, "kind": kind, **fields}
    names = ", ".join(cols)                      # column names come from our own code only
    marks = ", ".join("?" for _ in cols)
    ticket_id = await db.insert(f"INSERT INTO tickets ({names}) VALUES ({marks})", tuple(cols.values()))

    base_name = f"{slug}-{ticket_id:04d}"
    try:
        channel = await create_ticket_channel(
            guild, member, base_name, kind, topic=f"{kind} ticket #{ticket_id} for {member}"
        )
    except discord.HTTPException:
        await db.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
        raise

    await db.execute("UPDATE tickets SET channel_id=?, base_name=? WHERE id=?",
                     (channel.id, base_name, ticket_id))
    return ticket_id, channel


# ------------------------------------------------------ refresh the buttons
async def refresh_ticket_message(channel: discord.TextChannel, ticket_id: int):
    """Rebuild the button row from the database (Claimed / MM Requested / decisions)."""
    from utils.ticket_views import VIEW_FOR_KIND       # lazy import avoids a circular import
    t = await db.fetchone("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not t or not t["message_id"]:
        return
    view = VIEW_FOR_KIND[t["kind"]]()
    for child in view.children:
        cid = getattr(child, "custom_id", "") or ""
        if cid.endswith(":claim") and t["claimed_by"]:
            child.label, child.disabled = "Claimed", True
        elif cid.endswith(":mm") and t["mm_requested"]:
            child.label, child.disabled = "MM Requested", True
        elif cid.endswith((":accept", ":deny")) and t["decision"]:
            child.disabled = True
    try:
        message = await channel.fetch_message(t["message_id"])
        await message.edit(view=view)
    except discord.HTTPException:
        pass


# ------------------------------------------------------------ claim / unclaim
async def do_claim(member: discord.Member, channel: discord.TextChannel):
    t = await get_ticket(channel.id)
    if not t or t["status"] != "open":
        return False, "This is not an open ticket."
    if not await member_has_kind(member, KIND_ROLE[t["kind"]]):
        return False, "You don't have the role needed to claim this type of ticket."

    # atomic: only succeeds if nobody claimed it yet
    changed = await db.execute(
        "UPDATE tickets SET claimed_by=? WHERE id=? AND claimed_by IS NULL", (member.id, t["id"])
    )
    if not changed:
        return False, "This ticket is already claimed."

    asyncio.create_task(rename_channel(channel, f"claimed-{clean_name(member.name)}"))
    await refresh_ticket_message(channel, t["id"])
    return True, ""


async def do_unclaim(member: discord.Member, channel: discord.TextChannel):
    t = await get_ticket(channel.id)
    if not t or t["status"] != "open":
        return False, "This is not an open ticket."
    if not t["claimed_by"]:
        return False, "This ticket isn't claimed."
    if t["completed"]:
        return False, "This deal is already completed."
    if t["claimed_by"] != member.id and not await member_has_kind(member, "manager"):
        return False, "Only the person who claimed it (or a manager) can unclaim."

    await db.execute("UPDATE tickets SET claimed_by=NULL WHERE id=?", (t["id"],))
    if t["base_name"]:
        asyncio.create_task(rename_channel(channel, t["base_name"]))
    await refresh_ticket_message(channel, t["id"])
    return True, ""


async def claim_button(interaction: discord.Interaction):
    await interaction.response.defer()
    ok, msg = await do_claim(interaction.user, interaction.channel)
    if ok:
        await interaction.followup.send(f"✅ Ticket claimed by {interaction.user.mention}.")
    else:
        await interaction.followup.send(msg, ephemeral=True)


# ----------------------------------------------------------- request middleman
async def request_mm(interaction: discord.Interaction):
    t = await get_ticket(interaction.channel_id)
    if not t or t["status"] != "open":
        return await interaction.response.send_message("This is not an open ticket.", ephemeral=True)

    allowed = interaction.user.id == t["user_id"] or await member_has_kind(
        interaction.user, KIND_ROLE[t["kind"]]
    )
    if not allowed:
        return await interaction.response.send_message("Only the client or staff can request a middleman.", ephemeral=True)

    mm_roles = await role_ids_for(interaction.guild_id, "middleman")
    if not mm_roles:
        return await interaction.response.send_message(
            "No middleman roles are configured. An admin must run `,addrole middleman @role`.", ephemeral=True
        )

    changed = await db.execute(
        "UPDATE tickets SET mm_requested=1 WHERE id=? AND mm_requested=0", (t["id"],)
    )
    if not changed:
        return await interaction.response.send_message("A middleman was already requested.", ephemeral=True)

    await interaction.response.defer()
    pings = []
    for rid in mm_roles:
        role = interaction.guild.get_role(rid)
        if role:
            await interaction.channel.set_permissions(
                role, view_channel=True, send_messages=True, read_message_history=True, attach_files=True
            )
            pings.append(role.mention)

    await refresh_ticket_message(interaction.channel, t["id"])
    await interaction.followup.send(
        f"🛡️ {' '.join(pings)} A middleman was requested by {interaction.user.mention}.",
        allowed_mentions=PINGS,
    )


# ------------------------------------------------------------- close flow
class CloseView(discord.ui.View):
    def __init__(self, user_id: int, can_complete: bool):
        super().__init__(timeout=60)
        self.user_id = user_id
        if not can_complete:
            self.remove_item(self.complete_close)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Deal completed & close", emoji="✅", style=discord.ButtonStyle.success)
    async def complete_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Logging the deal and closing...", view=None)
        ok, msg = await complete_deal(interaction.guild, interaction.channel, interaction.user)
        if not ok:
            return await interaction.followup.send(msg, ephemeral=True)
        await close_ticket(interaction.channel, interaction.user)

    @discord.ui.button(label="Close ticket", emoji="🔒", style=discord.ButtonStyle.danger)
    async def plain_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Closing ticket...", view=None)
        await close_ticket(interaction.channel, interaction.user)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled.", view=None)


async def open_close_prompt(user: discord.Member, channel_id: int, send):
    """`send` is an async function taking message kwargs (content, view)."""
    t = await get_ticket(channel_id)
    if not t or t["status"] != "open":
        return await send(content="This is not an open ticket.")

    is_staff = await member_has_kind(user, KIND_ROLE[t["kind"]])
    if not (is_staff or user.id == t["user_id"]):
        return await send(content="Only staff or the ticket owner can close this ticket.")

    can_complete = False
    if t["kind"] == "exchange" and is_staff and t["claimed_by"] and not t["completed"]:
        can_complete = t["claimed_by"] == user.id or await member_has_kind(user, "manager")

    if can_complete:
        text = "Was this deal **completed**? Completing it logs the deal and adds it to the stats."
    elif t["kind"] == "exchange" and is_staff and not t["claimed_by"] and not t["completed"]:
        text = "This ticket isn't claimed, so it can only be closed **without** a completed deal."
    else:
        text = "Close this ticket?"

    await send(content=text, view=CloseView(user.id, can_complete))


async def close_button(interaction: discord.Interaction):
    async def send(**kwargs):
        await interaction.response.send_message(ephemeral=True, **kwargs)
    await open_close_prompt(interaction.user, interaction.channel_id, send)


# ----------------------------------------------------------- complete a deal
async def complete_deal(guild: discord.Guild, channel: discord.TextChannel, staff: discord.Member):
    t = await get_ticket(channel.id)
    if not t or t["kind"] != "exchange":
        return False, "Only exchange tickets can be completed."
    if t["completed"]:
        return True, ""
    if not t["claimed_by"]:
        return False, "Claim the ticket first."
    if t["claimed_by"] != staff.id and not await member_has_kind(staff, "manager"):
        return False, "Only the staff member who claimed this ticket can complete it."

    tax_pct = await get_tax_percent(guild.id)
    tax = round((t["amount_usd"] or 0) * tax_pct / 100, 4)

    changed = await db.execute(
        "UPDATE tickets SET completed=1, completed_at=CURRENT_TIMESTAMP, tax_usd=? "
        "WHERE id=? AND completed=0",
        (tax, t["id"]),
    )
    if not changed:
        return True, ""

    cfg = EX_TYPES.get(t["ex_type"], {})
    embed = discord.Embed(title="Deal Logged", color=0x57F287)
    embed.add_field(name="Ticket", value=f"#{t['id']:04d}")
    embed.add_field(name="Client", value=f"<@{t['user_id']}>")
    embed.add_field(name="Handled by", value=f"<@{t['claimed_by']}>")
    embed.add_field(name="Category", value=cfg.get("category", "-"))
    embed.add_field(name="Amount", value=f"${t['amount_usd']:,.2f}")
    embed.add_field(name="Exchange", value=f"{t['send_asset']} -> {t['recv_asset']}")
    embed.add_field(name="Calculation", value=t["calc_text"] or "-", inline=False)
    embed.add_field(name="Tax recorded", value=f"${tax:,.4f} ({tax_pct:g}%)")

    log_id = await db.get_setting(guild.id, "deal_log_channel")
    if log_id:
        log_channel = guild.get_channel(int(log_id))
        if log_channel:
            await log_channel.send(embed=embed)
    return True, ""


# ------------------------------------------------------------------- close
async def close_ticket(channel: discord.TextChannel, closer: discord.abc.User):
    guild = channel.guild
    t = await get_ticket(channel.id)

    data = await build_transcript(channel)
    filename = f"transcript-{channel.name}.html"

    if t:
        await db.execute(
            "UPDATE tickets SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE id=?", (t["id"],)
        )

    log_id = await db.get_setting(guild.id, "transcript_channel")
    if log_id:
        log_channel = guild.get_channel(int(log_id))
        if log_channel:
            embed = discord.Embed(title="Ticket Closed", color=EMBED_COLOR)
            embed.add_field(name="Channel", value=channel.name)
            embed.add_field(name="Closed by", value=closer.mention)
            if t:
                embed.add_field(name="Type", value=t["kind"])
                embed.add_field(name="Opened by", value=f"<@{t['user_id']}>")
                embed.add_field(name="Claimed by", value=f"<@{t['claimed_by']}>" if t["claimed_by"] else "Nobody")
                embed.add_field(name="Deal completed", value="Yes" if t["completed"] else "No")
            await log_channel.send(embed=embed, file=discord.File(io.BytesIO(data), filename=filename))

    if t:
        member = guild.get_member(t["user_id"])
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

### 8.6 `utils/ticket_views.py`: the buttons inside tickets

These are the three persistent button rows. Custom IDs are fixed so buttons survive restarts.

```python
# utils/ticket_views.py
import discord
import database as db
from utils import tickets
from utils.checks import member_has_kind


class ExchangeTicketView(discord.ui.View):
    """Claim (green) | Req MM (grey) | Close (red)"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="exchange:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.claim_button(interaction)

    @discord.ui.button(label="Req MM", style=discord.ButtonStyle.secondary, custom_id="exchange:mm")
    async def mm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.request_mm(interaction)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="exchange:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.close_button(interaction)


class SupportTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="support:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.claim_button(interaction)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="support:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.close_button(interaction)


async def _decide(interaction: discord.Interaction, accepted: bool):
    t = await tickets.get_ticket(interaction.channel_id)
    if not t or t["status"] != "open":
        return await interaction.response.send_message("This is not an open application.", ephemeral=True)
    if not await member_has_kind(interaction.user, "application"):
        return await interaction.response.send_message(
            "Only the Owner / Founder roles can decide applications.", ephemeral=True
        )

    decision = "accepted" if accepted else "denied"
    changed = await db.execute(
        "UPDATE tickets SET decision=? WHERE id=? AND decision IS NULL", (decision, t["id"])
    )
    if not changed:
        return await interaction.response.send_message("A decision was already made.", ephemeral=True)

    await interaction.response.defer()
    await tickets.refresh_ticket_message(interaction.channel, t["id"])

    embed = discord.Embed(
        title=f"Application {decision.title()}",
        description=f"Decision by {interaction.user.mention}.",
        color=0x57F287 if accepted else 0xED4245,
    )
    await interaction.followup.send(embed=embed)

    try:
        user = interaction.guild.get_member(t["user_id"]) or await interaction.client.fetch_user(t["user_id"])
        await user.send(
            f"Your staff application in **{interaction.guild.name}** was **{decision}**."
            + (" A manager will contact you soon." if accepted else "")
        )
    except discord.HTTPException:
        pass


class ApplyTicketView(discord.ui.View):
    """Only Owner/Founder (role kind 'application') can use these."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="apply:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.claim_button(interaction)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.primary, custom_id="apply:accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _decide(interaction, True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.secondary, custom_id="apply:deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _decide(interaction, False)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="apply:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await tickets.close_button(interaction)


VIEW_FOR_KIND = {
    "exchange": ExchangeTicketView,
    "support": SupportTicketView,
    "apply": ApplyTicketView,
}
```

---

## Part 9: `bot.py`

```python
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
```

---

## Part 10: Cogs

### 10.1 `cogs/setup_cog.py`: setup, roles, rates

```python
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
```

### 10.2 `cogs/exchange.py`: the panel, pickers, form and ticket

This is the file that produces the reference UI. Section 11 maps each screenshot element to its line.

```python
# cogs/exchange.py
import math
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands

import database as db
from config import (BRAND, EMBED_COLOR, EX_TYPES, INR_METHODS, CRYPTOS, LOGO_PATH,
                    PANEL_AMOUNT_TEXT, MIN_USD, TIMEZONE)
from utils import tickets
from utils.calc import calculate, get_rate, get_c2c_fee
from utils.checks import require, SafeModal
from utils.ticket_views import ExchangeTicketView


def enabled_types() -> dict:
    return {k: v for k, v in EX_TYPES.items() if v["enabled"]}


# ============================================================== PANEL EMBED
async def build_panel_embed(guild_id: int) -> discord.Embed:
    lines = ["# SECURE EXCHANGE SERVICE", "", "Live staff • Private tickets • Fast handling", ""]
    for key, cfg in enabled_types().items():
        if key == "crypto_to_crypto":
            info = f"{PANEL_AMOUNT_TEXT} • {await get_c2c_fee(guild_id):g}% fee"
        else:
            info = f"{PANEL_AMOUNT_TEXT} • {await get_rate(guild_id, key):g} / $"
        lines += [f"**{cfg['panel_title']}**", info, ""]
    lines.append("Select an exchange type below")

    embed = discord.Embed(description="\n".join(lines), color=EMBED_COLOR)
    embed.set_author(name=BRAND)                              # small brand line at the top
    if os.path.exists(LOGO_PATH):
        embed.set_thumbnail(url="attachment://logo.png")      # logo on the right
    return embed


# ======================================================= STEP 1: DROPDOWN
class ExchangeTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cfg["label"], value=key, description=f"{cfg['category']} exchange")
            for key, cfg in enabled_types().items()
        ]
        super().__init__(placeholder="Choose an exchange type", options=options,
                         custom_id="exchange:type")

    async def callback(self, interaction: discord.Interaction):
        ex_type = self.values[0]

        existing = await tickets.existing_open(interaction.guild_id, interaction.user.id, "exchange")
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket: <#{existing['channel_id']}>", ephemeral=True
            )
        else:
            view = OptionsView(ex_type)
            await interaction.response.send_message(
                "Pick your options, then press **Continue**.", view=view, ephemeral=True
            )
            view.origin = interaction          # remembered so we can delete this message later

        # reset the dropdown so the same option can be picked again
        try:
            await interaction.message.edit(view=ExchangePanelView())
        except discord.HTTPException:
            pass


class ExchangePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ExchangeTypeSelect())


# ================================================ STEP 2: THE TWO DROPDOWNS
class ChoiceSelect(discord.ui.Select):
    def __init__(self, placeholder: str, choices: list, attr: str, row: int):
        super().__init__(
            placeholder=placeholder,
            options=[discord.SelectOption(label=label, value=value) for label, value in choices],
            row=row,
        )
        self.attr = attr

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        setattr(self.view, self.attr, chosen)
        for opt in self.options:                       # show the choice inside the dropdown
            opt.default = opt.value == chosen
        await interaction.response.edit_message(view=self.view)


class OptionsView(discord.ui.View):
    """First dropdown = what you SEND, second = what you RECEIVE."""
    def __init__(self, ex_type: str):
        super().__init__(timeout=300)
        self.ex_type = ex_type
        self.send = None
        self.recv = None
        self.origin: discord.Interaction | None = None

        inr = list(INR_METHODS.items())                 # (label, code)
        crypto = [(c, c) for c in CRYPTOS]

        if ex_type == "inr_to_crypto":
            first, second = inr, crypto
        elif ex_type == "crypto_to_inr":
            first, second = crypto, inr
        else:
            first, second = crypto, crypto

        self.add_item(ChoiceSelect("What are you SENDING?", first, "send", row=0))
        self.add_item(ChoiceSelect("What do you want to RECEIVE?", second, "recv", row=1))

    async def dismiss(self):
        """Delete the picker message (called after the ticket is created or on timeout)."""
        self.stop()
        if self.origin:
            try:
                await self.origin.delete_original_response()
            except discord.HTTPException:
                pass

    async def on_timeout(self):
        await self.dismiss()

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success, row=2)
    async def go(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.send or not self.recv:
            return await interaction.response.send_message("Please choose both options first.", ephemeral=True)
        if self.send == self.recv:
            return await interaction.response.send_message("Sending and receiving can't be the same.", ephemeral=True)
        await interaction.response.send_modal(DetailsModal(self))


# =========================================================== STEP 3: FORM
class DetailsModal(SafeModal):
    def __init__(self, picker: OptionsView):
        super().__init__(title="Exchange details")
        self.picker = picker
        self.amount = discord.ui.TextInput(label="Exchange amount (USD)", placeholder="e.g. 5", max_length=10)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        p = self.picker
        cfg = EX_TYPES[p.ex_type]

        try:
            amount = float(self.amount.value.replace(",", "").replace("$", "").strip())
        except ValueError:
            return await interaction.followup.send("Amount must be a number.", ephemeral=True)
        if not math.isfinite(amount) or amount <= 0:
            return await interaction.followup.send("Enter a valid positive amount.", ephemeral=True)
        if amount < MIN_USD:
            return await interaction.followup.send(f"Minimum amount is ${MIN_USD:g}.", ephemeral=True)

        existing = await tickets.existing_open(interaction.guild_id, interaction.user.id, "exchange")
        if existing:
            return await interaction.followup.send(
                f"You already have an open ticket: <#{existing['channel_id']}>", ephemeral=True
            )

        calc = await calculate(interaction.guild_id, p.ex_type, amount, p.send, p.recv)

        try:
            ticket_id, channel = await tickets.new_ticket(
                interaction.guild, interaction.user, "exchange", cfg["slug"],
                {
                    "ex_type": p.ex_type, "send_asset": p.send, "recv_asset": p.recv,
                    "amount_usd": amount, "inr_amount": calc["inr_amount"], "rate": calc["rate"],
                    "fee_usd": calc["fee_usd"], "calc_text": calc["calc_text"],
                },
            )
        except discord.HTTPException:
            return await interaction.followup.send(
                "I couldn't create the ticket channel. Ask an admin to check my permissions and the ticket category.",
                ephemeral=True,
            )

        pings = await tickets.staff_pings(interaction.guild, "exchange")
        message = await channel.send(
            content=f"{pings} {interaction.user.mention}".strip(),
            embed=ticket_embed(interaction.user, cfg, amount, p.send, p.recv, calc),
            view=ExchangeTicketView(),
            allowed_mentions=tickets.PINGS,
        )
        await db.execute("UPDATE tickets SET message_id=? WHERE id=?", (message.id, ticket_id))

        await p.dismiss()                                   # picker message deletes itself
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


# ===================================================== THE TICKET EMBED
def ticket_embed(member: discord.Member, cfg: dict, amount: float, send: str, recv: str, calc: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"{BRAND} — Transaction Details",
        description="Your ticket will shortly be reviewed by an exchanger.\nPlease wait patiently.",
        color=EMBED_COLOR,
    )
    embed.add_field(name="Client", value=f"{member.mention}\n`{member.id}`", inline=False)
    embed.add_field(name="Category", value=f"`{cfg['category']}`", inline=False)
    embed.add_field(name="Amount", value=f"`${amount:,.2f}`", inline=False)
    embed.add_field(name="Exchange", value=f"`{send} -> {recv}`", inline=False)
    embed.add_field(name="You Sending", value=f"`{send}`", inline=False)
    embed.add_field(name="You Receiving", value=f"`{recv}`", inline=False)
    embed.add_field(name="Auto Calculation", value=f"`{calc['calc_text']}`", inline=False)
    now = datetime.now(ZoneInfo(TIMEZONE))
    embed.set_footer(text=f"Requested by {member.name} • Confirmed | {now:%d/%m/%Y %H:%M}")
    return embed


# ================================================================== COG
class ExchangeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(ExchangePanelView())
        self.bot.add_view(ExchangeTicketView())

    @commands.hybrid_command(name="exchangepanel", description="Post the exchange panel in this channel")
    @require("manager")
    @commands.guild_only()
    async def exchangepanel(self, ctx: commands.Context):
        file = discord.File(LOGO_PATH, filename="logo.png") if os.path.exists(LOGO_PATH) else None
        await ctx.channel.send(embed=await build_panel_embed(ctx.guild.id), view=ExchangePanelView(), file=file)
        if ctx.interaction:
            await ctx.send("Panel posted.", ephemeral=True)
        else:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ExchangeCog(bot))
```

### 10.3 `cogs/support.py`: support tickets and staff-application tickets

Support tickets are visible to **support** roles. Application tickets are visible to **application** roles only (Owner/Founder), so exchangers and support staff cannot see them.

```python
# cogs/support.py
import os
import discord
from discord.ext import commands

import database as db
from config import BRAND, EMBED_COLOR, LOGO_PATH
from utils import tickets
from utils.checks import require, SafeModal
from utils.ticket_views import SupportTicketView, ApplyTicketView


# ============================================================ SUPPORT
class SupportModal(SafeModal):
    def __init__(self):
        super().__init__(title="Support request")
        self.issue = discord.ui.TextInput(label="Describe your issue", style=discord.TextStyle.paragraph,
                                          max_length=1000)
        self.add_item(self.issue)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        existing = await tickets.existing_open(interaction.guild_id, interaction.user.id, "support")
        if existing:
            return await interaction.followup.send(
                f"You already have an open support ticket: <#{existing['channel_id']}>", ephemeral=True)

        try:
            ticket_id, channel = await tickets.new_ticket(
                interaction.guild, interaction.user, "support", "support", {})
        except discord.HTTPException:
            return await interaction.followup.send("I couldn't create the ticket.", ephemeral=True)

        embed = discord.Embed(
            title=f"{BRAND} — Support Ticket",
            description="A support member will be with you shortly.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Client", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=False)
        embed.add_field(name="Issue", value=self.issue.value, inline=False)

        pings = await tickets.staff_pings(interaction.guild, "support")
        message = await channel.send(
            content=f"{pings} {interaction.user.mention}".strip(),
            embed=embed, view=SupportTicketView(), allowed_mentions=tickets.PINGS,
        )
        await db.execute("UPDATE tickets SET message_id=? WHERE id=?", (message.id, ticket_id))
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


class SupportPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Support Ticket", emoji="🎫", style=discord.ButtonStyle.primary,
                       custom_id="support:open")
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SupportModal())


# ========================================================== APPLICATIONS
class ApplyModal(SafeModal):
    def __init__(self):
        super().__init__(title="Staff application")
        self.age = discord.ui.TextInput(label="Age", max_length=3)
        self.experience = discord.ui.TextInput(label="Exchange / moderation experience",
                                               style=discord.TextStyle.paragraph, max_length=800)
        self.why = discord.ui.TextInput(label="Why should we pick you?",
                                        style=discord.TextStyle.paragraph, max_length=800)
        self.availability = discord.ui.TextInput(label="Timezone and daily availability", max_length=100)
        for item in (self.age, self.experience, self.why, self.availability):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        existing = await tickets.existing_open(interaction.guild_id, interaction.user.id, "apply")
        if existing:
            return await interaction.followup.send(
                f"You already have an open application: <#{existing['channel_id']}>", ephemeral=True)

        try:
            ticket_id, channel = await tickets.new_ticket(
                interaction.guild, interaction.user, "apply", "apply", {})
        except discord.HTTPException:
            return await interaction.followup.send("I couldn't create the application ticket.", ephemeral=True)

        embed = discord.Embed(title=f"{BRAND} — Staff Application", color=EMBED_COLOR)
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Applicant", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=False)
        embed.add_field(name="Age", value=f"`{self.age.value}`")
        embed.add_field(name="Availability", value=f"`{self.availability.value}`")
        embed.add_field(name="Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Why them", value=self.why.value, inline=False)

        pings = await tickets.staff_pings(interaction.guild, "apply")      # Owner / Founder only
        message = await channel.send(
            content=f"{pings} {interaction.user.mention}".strip(),
            embed=embed, view=ApplyTicketView(), allowed_mentions=tickets.PINGS,
        )
        await db.execute("UPDATE tickets SET message_id=? WHERE id=?", (message.id, ticket_id))
        await interaction.followup.send(f"✅ Application submitted: {channel.mention}", ephemeral=True)


class ApplyPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply for Staff", emoji="📝", style=discord.ButtonStyle.primary,
                       custom_id="apply:open")
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplyModal())


# ================================================================== COG
class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        for view in (SupportPanelView(), SupportTicketView(), ApplyPanelView(), ApplyTicketView()):
            self.bot.add_view(view)

    async def _post(self, ctx: commands.Context, embed: discord.Embed, view: discord.ui.View):
        file = discord.File(LOGO_PATH, filename="logo.png") if os.path.exists(LOGO_PATH) else None
        if file:
            embed.set_thumbnail(url="attachment://logo.png")
        await ctx.channel.send(embed=embed, view=view, file=file)
        if ctx.interaction:
            await ctx.send("Panel posted.", ephemeral=True)
        else:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass

    @commands.hybrid_command(name="supportpanel", description="Post the support ticket panel")
    @require("manager")
    @commands.guild_only()
    async def supportpanel(self, ctx: commands.Context):
        embed = discord.Embed(
            description="# SUPPORT\n\nNeed help with a deal or have a question?\nOpen a ticket and our team will assist you.",
            color=EMBED_COLOR)
        embed.set_author(name=BRAND)
        await self._post(ctx, embed, SupportPanelView())

    @commands.hybrid_command(name="applypanel", description="Post the staff application panel")
    @require("manager")
    @commands.guild_only()
    async def applypanel(self, ctx: commands.Context):
        embed = discord.Embed(
            description="# STAFF APPLICATIONS\n\nWant to join the team?\nPress the button and fill in the form.",
            color=EMBED_COLOR)
        embed.set_author(name=BRAND)
        await self._post(ctx, embed, ApplyPanelView())


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportCog(bot))
```

### 10.4 `cogs/ticket_commands.py`: `,claim` `,uc` `,v` `,3p` `,close` `,transcript`

```python
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
```

⚠️ `,3p` toggles: run it once to add someone, again on the same person to remove them.

### 10.5 `cogs/stats.py`: profiles, leaderboards, vouches, tax

```python
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
```

⚠️ How the manual tools work: `,addlb` adds to a separate "manual" amount, `,setlb` makes the user's **total** equal what you type (real deals + manual), `,resetlb` starts a new season by moving a start date forward, so no deal history is deleted. Manual edits only appear on `,lb`, not `,clb`.

### 10.6 `cogs/calculators.py`: calculators, rates, help

```python
# cogs/calculators.py
import math
import discord
from discord.ext import commands

from config import BRAND, EMBED_COLOR, PREFIX
from utils.calc import get_rate, get_c2c_fee, get_tax_percent


def positive(*values: float):
    for v in values:
        if not math.isfinite(v) or v <= 0:
            raise commands.BadArgument("All numbers must be positive.")


class Calculators(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _embed(self, title: str, **fields) -> discord.Embed:
        embed = discord.Embed(title=title, color=EMBED_COLOR)
        for name, value in fields.items():
            embed.add_field(name=name.replace("_", " "), value=value, inline=False)
        return embed

    @commands.hybrid_command(name="i2c", description="INR to Crypto: how much $ of crypto does this INR buy?")
    @commands.guild_only()
    async def i2c(self, ctx: commands.Context, inr: float):
        positive(inr)
        rate = await get_rate(ctx.guild.id, "inr_to_crypto")
        await ctx.send(embed=self._embed("INR → Crypto",
            You_pay=f"`Rs.{inr:,.2f}`", You_receive=f"`${inr / rate:,.2f}` of crypto", Rate=f"`{rate:g} / $`"))

    @commands.hybrid_command(name="c2i", description="Crypto to INR: how much INR for this $ amount?")
    @commands.guild_only()
    async def c2i(self, ctx: commands.Context, usd: float):
        positive(usd)
        rate = await get_rate(ctx.guild.id, "crypto_to_inr")
        await ctx.send(embed=self._embed("Crypto → INR",
            You_send=f"`${usd:,.2f}`", You_receive=f"`Rs.{usd * rate:,.2f}`", Rate=f"`{rate:g} / $`"))

    @commands.hybrid_command(name="c2c", description="Crypto to Crypto: amount received after the fee")
    @commands.guild_only()
    async def c2c(self, ctx: commands.Context, usd: float):
        positive(usd)
        fee = await get_c2c_fee(ctx.guild.id)
        cut = usd * fee / 100
        await ctx.send(embed=self._embed("Crypto → Crypto",
            You_send=f"`${usd:,.2f}`", Fee=f"`${cut:,.2f}` ({fee:g}%)", You_receive=f"`${usd - cut:,.2f}`"))

    # ⚠️ The three "rate" calculators work with a coin price you type in.
    @commands.hybrid_command(name="cr2i", description="Coins at a USD price → INR you receive")
    @commands.guild_only()
    async def cr2i(self, ctx: commands.Context, coins: float, price_usd: float):
        positive(coins, price_usd)
        rate = await get_rate(ctx.guild.id, "crypto_to_inr")
        value = coins * price_usd
        await ctx.send(embed=self._embed("Crypto rate → INR",
            Value=f"`{coins:g} × ${price_usd:,.4f} = ${value:,.2f}`", You_receive=f"`Rs.{value * rate:,.2f}`",
            Rate=f"`{rate:g} / $`"))

    @commands.hybrid_command(name="cr2c", description="INR amount → how many coins at a USD price")
    @commands.guild_only()
    async def cr2c(self, ctx: commands.Context, inr: float, price_usd: float):
        positive(inr, price_usd)
        rate = await get_rate(ctx.guild.id, "inr_to_crypto")
        usd = inr / rate
        await ctx.send(embed=self._embed("INR → coins at your price",
            You_pay=f"`Rs.{inr:,.2f}`", Worth=f"`${usd:,.2f}`", Coins=f"`{usd / price_usd:,.6f}`",
            Rate=f"`{rate:g} / $`"))

    @commands.hybrid_command(name="c2cr", description="Coin A → coin B quantity after the fee, using USD prices")
    @commands.guild_only()
    async def c2cr(self, ctx: commands.Context, coins: float, from_price_usd: float, to_price_usd: float):
        positive(coins, from_price_usd, to_price_usd)
        fee = await get_c2c_fee(ctx.guild.id)
        value = coins * from_price_usd
        net = value * (1 - fee / 100)
        await ctx.send(embed=self._embed("Coin → coin",
            You_send=f"`{coins:g}` (≈ ${value:,.2f})", Fee=f"`{fee:g}%`", You_receive=f"`{net / to_price_usd:,.6f}`"))

    @commands.hybrid_command(name="rates", description="Show the current rates")
    @commands.guild_only()
    async def rates(self, ctx: commands.Context):
        gid = ctx.guild.id
        await ctx.send(embed=self._embed(f"{BRAND} — Rates",
            INR_to_Crypto=f"`{await get_rate(gid, 'inr_to_crypto'):g} / $`",
            Crypto_to_INR=f"`{await get_rate(gid, 'crypto_to_inr'):g} / $`",
            Crypto_to_Crypto_fee=f"`{await get_c2c_fee(gid):g}%`",
            Staff_tax=f"`{await get_tax_percent(gid):g}%`"))

    @commands.hybrid_command(name="help", description="Show all commands")
    async def help_cmd(self, ctx: commands.Context):
        p = PREFIX
        embed = discord.Embed(title=f"{BRAND} — Commands", color=EMBED_COLOR)
        embed.add_field(name="Calculators", inline=False, value=(
            f"`{p}i2c <inr>` `{p}c2i <usd>` `{p}c2c <usd>`\n"
            f"`{p}cr2i <coins> <price>` `{p}cr2c <inr> <price>` `{p}c2cr <coins> <from> <to>` `{p}rates`"))
        embed.add_field(name="Profiles & boards", inline=False, value=(
            f"`{p}p [@user]` `{p}deals [@user]` `{p}lb [users|staff]` `{p}clb [users|staff]`"))
        embed.add_field(name="Tickets (staff)", inline=False, value=(
            f"`{p}claim` `{p}uc` `{p}v` `{p}3p @user` `{p}close` `{p}transcript`\n"
            f"`{p}e @user [note]` `{p}mytax`"))
        embed.add_field(name="Managers", inline=False, value=(
            f"`{p}setrate` `{p}setfee` `{p}settax` `{p}stafffees` `{p}cleartax @user`\n"
            f"`{p}addlb` `{p}setlb` `{p}resetlb` `{p}exchangepanel` `{p}supportpanel` `{p}applypanel`"))
        embed.add_field(name="Admins", inline=False, value=(
            f"`{p}setup` `{p}addrole <kind> @role` `{p}removerole` `{p}roles`"))
        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Calculators(bot))
```

---

## Part 11: UI mapping

### 11.1 Panel: screenshot → code

| In the reference panel | In your code |
|---|---|
| Small bold brand line at the top ("Crix Exchanges") | `embed.set_author(name=BRAND)` in `build_panel_embed` |
| Logo on the right | `embed.set_thumbnail(url="attachment://logo.png")` + `discord.File(LOGO_PATH)` in `exchangepanel` |
| Huge "SECURE EXCHANGE SERVICE" | `# SECURE EXCHANGE SERVICE` (a Markdown heading inside the embed description) |
| "Live staff • Private tickets • Fast handling" | second description line |
| `INR → CRYPTO` / `Any amount • 104 / $` | `cfg['panel_title']` and `PANEL_AMOUNT_TEXT • rate / $`, rate read live from the database |
| "Select an exchange type below" | last description line |
| Dropdown under the embed | `ExchangeTypeSelect` inside `ExchangePanelView` |

Change the numbers any time with `,setrate inr_to_crypto 105`. Then post the panel again (or edit it by deleting the old one and re-running `,exchangepanel`).

### 11.2 Picker: screenshot → code

| In the reference | In your code |
|---|---|
| "Pick your options, then press **Continue**." | message content in `ExchangeTypeSelect.callback` |
| Two dropdowns (e.g. Fampay, USDT) | two `ChoiceSelect` items; chosen value is shown via `opt.default` |
| Green **Continue** | `OptionsView.go` button |
| "Only you can see this • Dismiss message" | `ephemeral=True` |
| **"auto reset and delete" after the ticket is created** | `p.dismiss()` runs `origin.delete_original_response()` right after the ticket message is sent; it also runs on timeout (5 minutes); the panel dropdown resets itself via `interaction.message.edit(view=ExchangePanelView())` |

### 11.3 Ticket: screenshot → code

| In the reference ticket | In your code |
|---|---|
| Ping line: roles + client | `content=f"{pings} {user.mention}"` using `staff_pings()` (every role set with `,addrole exchanger`) |
| "Transaction Details" title | `title=f"{BRAND} — Transaction Details"` |
| "Your ticket will shortly be reviewed by an exchanger. Please wait patiently." | embed description |
| Client (mention + ID in code box) | `Client` field |
| Category `Crypto 2 INR` | `Category` field from `EX_TYPES[...]["category"]` |
| Amount `$5.00` | `Amount` field |
| Exchange `SOL -> GPAY` | `Exchange` field from the two dropdown values |
| You Sending / You Receiving | two fields |
| Auto Calculation `Rs.510.00 INR will be received` | `calc['calc_text']` from `utils/calc.py` |
| Footer "Requested by … • Confirmed \| 16/10/2026 18:43" | `embed.set_footer(...)` using `TIMEZONE` |
| Green **Claimed** | `Claim` button; after a claim it becomes disabled and renamed **Claimed** (`refresh_ticket_message`) |
| Grey **Req MM** | `Req MM` button → pings middleman roles and adds them to the channel |
| Red **Close** | `Close` button → confirmation, with a "Deal completed & close" option for the claiming staff member |
| Channel renamed `claimed-strawhat` | `do_claim` renames to `claimed-<staffname>`; `,uc` restores the original name |

### 11.4 Where the roles apply

| Ticket type | Who sees and can claim it | Who gets pinged |
|---|---|---|
| Exchange | `exchanger` roles (+ `manager` roles, + admins) | `exchanger` roles |
| Support | `support` roles (+ `manager`, + admins) | `support` roles |
| Staff application | `application` roles (+ `manager`, + admins). Exchangers and support staff **cannot see it** | `application` roles |

---

## Part 12: Discord server layout

```
EXCHANGE            (category)
  #exchange         ← run ,exchangepanel here
  #support          ← run ,supportpanel here
  #apply            ← run ,applypanel here
TICKETS             (category: the bot creates ticket channels here)
STAFF ONLY          (category, private)
  #deal-logs
  #transcripts
```

Roles to create (names are yours): **Senior Exchanger**, **Junior Exchanger**, **Support Staff**, **Owner**, **Founder**, **Middleman**.

### Permissions that must be right

1. **STAFF ONLY** is hidden from `@everyone`, but you must add the **bot** (its role) to that category with View Channel, Send Messages, Embed Links, Attach Files. Otherwise deal logs and transcripts fail silently.
2. The bot's role needs, server-wide or in TICKETS: View Channel, Manage Channels, Manage Roles, Send Messages, Embed Links, Attach Files, Read Message History. A bot can only hand out permissions it holds itself.
3. Drag the bot's role **above** your staff roles (Server Settings → Roles).
4. Make the staff roles **mentionable**, or keep the bot's Mention Everyone permission, so the ping works.
5. In `#exchange`, `#support` and `#apply`, deny `@everyone` the **Send Messages** permission so only the bot's panel is there (members can still use the dropdown and buttons).

---

## Part 13: First-time configuration

### 13.1 Run the bot

```bash
cd /home/mrrobot/Projects/assistance
source venv/bin/activate
python bot.py
```

Expected: `Logged in as <name> (ID: ...)`.

### 13.2 Configure (in your test server, as an admin)

```
,setup <ticket category> #deal-logs #transcripts
```

For the category, use its ID (right-click the category → Copy Category ID) or use the slash version `/setup`, which gives you pickers.

Then the roles (admin only):

```
,addrole exchanger @Senior Exchanger
,addrole exchanger @Junior Exchanger
,addrole support @Support Staff
,addrole application @Owner
,addrole application @Founder
,addrole manager @Owner
,addrole manager @Founder
,addrole middleman @Middleman
```

Check everything: `,roles`

Set your rates (managers/admins):

```
,setrate inr_to_crypto 104
,setrate crypto_to_inr 102
,settax 1
```

### 13.3 Post the panels

```
(in #exchange)  ,exchangepanel
(in #support)   ,supportpanel
(in #apply)     ,applypanel
```

---

## Part 14: Command reference

Every command works as `,name` and as `/name`.

### Calculators

| Command | Usage | Result |
|---|---|---|
| `,i2c` | `,i2c 520` | INR you pay → $ of crypto you get |
| `,c2i` | `,c2i 5` | $ you send → INR you receive |
| `,c2c` | `,c2c 50` | $ you send → $ received after the fee |
| `,cr2i` ⚠️ | `,cr2i 0.5 150` | 0.5 coins at $150 → INR received |
| `,cr2c` ⚠️ | `,cr2c 5000 150` | Rs.5000 → how many coins at $150 |
| `,c2cr` ⚠️ | `,c2cr 2 150 60000` | 2 coins of A (at $150) → coins of B (at $60000) after the fee |
| `,rates` | | Current rates, fee and tax |

### Profiles and boards

| Command | Who | Notes |
|---|---|---|
| `,p [@user]` / `,profile` | Anyone | Rank, deals, volume, all-time, handled deals, vouches |
| `,deals [@user]` | Anyone | Last 10 completed deals as client or handler |
| `,lb [users\|staff]` | Anyone | Leaderboard since the last reset (includes manual edits) |
| `,clb [users\|staff]` | Anyone | Current calendar month only |
| `,e @user [note]` ⚠️ | Exchangers | Adds a vouch / rep point to a user |
| `,mytax` ⚠️ | Exchangers | Your uncleared tax |
| `,stafffees` ⚠️ | Managers | Uncleared tax for all staff |
| `,cleartax @user` ⚠️ | Managers | Marks a staff member's tax as paid |
| `,addlb @user <deals> <usd>` ⚠️ | Managers | Adds to a user's board stats |
| `,setlb @user <deals> <usd>` ⚠️ | Managers | Sets a user's total board stats |
| `,resetlb` ⚠️ | Managers | Starts a new leaderboard (asks to confirm) |

### Tickets

| Command | Who | Notes |
|---|---|---|
| `,claim` | Staff for that ticket type | Same as the Claim button |
| `,uc` / `,unclaim` | The claimer or a manager | Restores the original channel name and re-enables Claim |
| `,v` ⚠️ | Client or exchanger | Prints a copy-and-paste vouch line (`VOUCH_FORMAT` in `config.py`) |
| `,3p @user` ⚠️ | Staff for that ticket type | Adds a third party to the ticket; run again to remove |
| `,close` | Staff or ticket owner | Same as the Close button |
| `,transcript` | Staff for that ticket type | Posts the transcript file in the ticket |

### Admin / manager

| Command | Who |
|---|---|
| `,setup <category> <#deal-logs> <#transcripts>` | Administrator |
| `,addrole <kind> @role`, `,removerole`, `,roles` | Administrator |
| `,setrate <type> <value>`, `,setfee`, `,settax` | Manager |
| `,exchangepanel`, `,supportpanel`, `,applypanel` | Manager |

⚠️ = behaviour is my interpretation of the one-line description from your reference bot's command list.

---

## Part 15: Testing checklist

Use a second Discord account as the customer.

### Panel and picker

| # | Test | Expected |
|---|---|---|
| 1 | `,exchangepanel` | Panel with logo, big title, `104 / $` and `102 / $`, dropdown |
| 2 | Pick **Crypto to INR** | Ephemeral picker with two dropdowns and **Continue** |
| 3 | Press Continue with nothing chosen | "Please choose both options first." |
| 4 | Choose `SOL` and `Google Pay`, Continue | Form asks for the USD amount |
| 5 | Enter `abc`, then `0.5` | "Amount must be a number." then "Minimum amount is $1." |
| 6 | Enter `5` | Ticket created; **the picker message disappears**; "✅ Ticket created" appears |
| 7 | Check the ticket | Pings, Transaction Details, `SOL -> GPAY`, `Rs.510.00 INR will be received`, footer, buttons Claim / Req MM / Close |
| 8 | Pick an exchange type again | "You already have an open ticket" |
| 9 | Open the picker and wait 5 minutes | The picker message deletes itself |

### Staff side

| # | Test | Expected |
|---|---|---|
| 10 | Customer presses Claim | "You don't have the role needed to claim this type of ticket." |
| 11 | Exchanger presses Claim | Button becomes **Claimed** (disabled), channel renamed `claimed-<name>` |
| 12 | `,uc` | Name restored, button becomes **Claim** again |
| 13 | Claim again, then press **Req MM** | Middleman role added to the channel and pinged; button becomes "MM Requested" |
| 14 | `,3p @someone` twice | Added, then removed |
| 15 | `,v` | Vouch line in a code block |
| 16 | `,transcript` | HTML file posted |
| 17 | Staff presses **Close** | Options: "Deal completed & close", "Close ticket", "Cancel" |
| 18 | Choose "Deal completed & close" | Deal Logged in `#deal-logs`, transcript in `#transcripts`, DM to client, channel deleted in 5 s |
| 19 | `,p @customer`, `,lb`, `,deals @customer` | The deal shows up |
| 20 | `,mytax` as the claimer | 1% of the deal volume (with the default tax) |
| 21 | `,stafffees` then `,cleartax @staff` | Shows then clears |
| 22 | `,addlb @user 3 100`, `,setlb @user 10 500`, `,lb` | Values change as described |
| 23 | `,resetlb` → Confirm | Leaderboard empties, `,deals` still shows history |

### Roles and support/apply

| # | Test | Expected |
|---|---|---|
| 24 | Open a **support** ticket | Only support roles are pinged and can see it; exchangers cannot |
| 25 | Open an **application** | Only Owner/Founder roles see and are pinged; Support and Exchanger roles **cannot** see it |
| 26 | Founder presses **Accept** | Buttons disable, decision posted, applicant gets a DM |
| 27 | A Support Staff user tries `,claim` in an application ticket | Denied |

### Reliability

| # | Test | Expected |
|---|---|---|
| 28 | **Restart the bot**, use the panel and ticket buttons again | Everything still works |
| 29 | `,setrate crypto_to_inr 110` then post a new ticket | New rate used; old tickets keep their old rate |
| 30 | A normal member types `,setrate ...` | "You don't have permission to use this command." |

---

## Part 16: Hosting

Your bot only works while the script is running.

| Option | Notes |
|---|---|
| **Your own Linux machine** | Free and reliable while it stays on. Use systemd (below). |
| **Oracle Cloud Always Free / Google Cloud e2-micro** | Free 24/7 VMs, but they need a card for signup and have no uptime guarantee. Check each provider's current free-tier terms on their official page. |
| **Cheap paid VPS** | Best for live customers (a few dollars a month). |
| **Random "free bot hosts"** | Avoid. Your bot holds a token and customer data. |

### systemd service (Linux)

```bash
sudo nano /etc/systemd/system/exchange-bot.service
```

```ini
[Unit]
Description=Discord Exchange Bot
After=network-online.target

[Service]
Type=simple
User=mrrobot
WorkingDirectory=/home/mrrobot/Projects/assistance
ExecStart=/home/mrrobot/Projects/assistance/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now exchange-bot
journalctl -u exchange-bot -f        # live logs
```

For production remove `DEV_GUILD_ID` from `.env` so slash commands sync globally.

### Back up the database daily

```bash
mkdir -p /home/mrrobot/backups
crontab -e
# add:
0 3 * * * cp /home/mrrobot/Projects/assistance/exchange.db /home/mrrobot/backups/exchange-$(date +\%F).db
```

---

## Part 17: Security, scams, legal

**Bot security**

- Keep the token only in `.env`. If it leaks, press Reset Token.
- Do not give the bot Administrator.
- All sensitive commands use `require(...)` role checks. Add the same to any command you create.
- SQL always uses `?` placeholders. The two places that format SQL text (`utils/checks.py` and `utils/tickets.py`) insert only `?` characters and hardcoded column names, never user input.

**Operational rules for staff**

- Never move funds outside the ticket channel or in DMs.
- Accept payment only from an account in the customer's own name.
- Release crypto only after the payment has actually **settled** in your account (screenshots can be faked, UPI and bank payments can be reversed).
- Crypto transfers are irreversible: check addresses and networks twice.
- Use **Req MM** for large or risky deals.
- Keep every transcript as evidence.

**Legal and platform**

Running an exchange service can bring AML/KYC, registration and tax obligations depending on your country (India has compliance and tax rules for virtual digital assets), and Discord has its own policies about what services servers may offer. This guide is technical help, not legal advice. Talk to a qualified professional before operating commercially.

The "staff tax" feature only keeps an internal ledger. It does not file or pay any real tax.

---

## Part 18: Customization recipes

| I want to… | Do this |
|---|---|
| Change the brand name | `BRAND` in `config.py`, then re-post the panel |
| Change the prefix | `PREFIX` in `config.py` |
| Change a rate | `,setrate inr_to_crypto 105` |
| Add a coin | Add it to `CRYPTOS` |
| Add or rename an INR method | Edit `INR_METHODS` (`"Google Pay": "GPAY"` = label: ticket code) |
| Turn Crypto to Crypto on | `"enabled": True` for `crypto_to_crypto`, set the fee with `,setfee 3`, re-post the panel |
| Make "Any amount" literal | `MIN_USD = 0.01` |
| Change the ticket footer time zone | `TIMEZONE` (a name like `Asia/Kolkata`) |
| Change the vouch line | `VOUCH_FORMAT` |
| Change the tax % | `,settax 2` |
| Give one role several powers | Run `,addrole` once per kind |
| Change embed colour | `EMBED_COLOR` |

---

## Part 19: Troubleshooting

| Problem | Fix |
|---|---|
| `PrivilegedIntentsRequired` | Turn on **Message Content Intent** in the Developer Portal → Bot |
| `,` commands do nothing | Message Content Intent off, or the bot can't see/send in that channel |
| Slash commands missing | Set `DEV_GUILD_ID`, restart the bot, restart Discord (Ctrl+R) |
| "I couldn't create the ticket channel" | Bot lacks Manage Channels or a permission it tries to grant; category full (50 channels); category missing (`,setup` again) |
| Role pings don't ping | Role not mentionable and the bot lacks Mention Everyone |
| Staff can't see tickets | Roles weren't added with `,addrole` (check `,roles`), or the roles were added **after** the ticket was created |
| Req MM or `,3p` fails | Bot lacks **Manage Roles** |
| Deal logs or transcripts missing | The bot can't see or send in `#deal-logs` / `#transcripts` (private category) |
| "You don't have the role needed to claim" | The user has no role set for that ticket kind. Admins always pass |
| Picker doesn't delete | It was opened more than 15 minutes ago (Discord's limit for editing interaction messages) |
| Channel rename is slow or skipped | Discord limits renames to 2 per 10 minutes per channel; the bot ignores the failure |
| Panel has no logo | `assets/logo.png` is missing, or you posted the panel before adding it. Re-post the panel |
| `ZoneInfoNotFoundError` | `pip install tzdata`, and check the `TIMEZONE` spelling |
| `sqlite3.OperationalError: no such column` | You are using the old v1 database: delete `exchange.db` |
| `ModuleNotFoundError: utils` | Run `python bot.py` from the project folder; check `utils/__init__.py` exists |
| Buttons dead after restart | Missing `timeout=None`, `custom_id`, or the `add_view` call in `cog_load` |
| "This interaction failed" | The handler took over 3 seconds without `defer()` |
| A cog fails to load | Read the traceback in the console; it names the file and line |

---

## Part 20: Final checklist

- [ ] Tested everything in Part 15 on a **test server**
- [ ] Your own brand name and logo in place (`BRAND`, `assets/logo.png`)
- [ ] Token only in `.env`; `.env` is in `.gitignore`
- [ ] Bot role above the staff roles, with the permissions in Part 12
- [ ] All role kinds configured (`,roles` shows no empty kinds you need)
- [ ] Rates, tax and fee set; panels posted
- [ ] `STAFF ONLY` channels private but visible to the bot
- [ ] Staff rules written (Part 17)
- [ ] Database backup scheduled
- [ ] Bot running as a service with auto-restart
- [ ] Local legal requirements checked

If something breaks, copy the exact console error and look it up in Part 19.
