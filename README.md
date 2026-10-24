# Discord Exchange Ticket Bot

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![discord.py](https://img.shields.io/badge/discord.py-2.4%2B-5865F2.svg)](https://discordpy.readthedocs.io/)
[![aiosqlite](https://img.shields.io/badge/storage-SQLite-orange.svg)](https://aiosqlite.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-working-brightgreen.svg)](https://github.com/ayux07/discord-exchange-bot)

A complete **INR ↔ Crypto exchange ticket bot** built with [`discord.py`](https://discordpy.readthedocs.io/).

It automates the workflow of running a peer-to-peer crypto exchange on Discord:
dropdown panels, private ticket channels, automatic calculations, staff
claim/complete/close buttons, HTML transcripts, deal logs, leaderboards,
vouches, staff tax tracking, support tickets and staff applications.

> Money and crypto transfers are done **manually by your staff**. This bot
> handles the workflow, calculations, logging and statistics.

---

## Screenshots

Add screenshots by dropping images into `assets/`, then link them here.

| Exchange panel | Ticket channel |
|---|---|
| ![Exchange panel](assets/panel.png) | ![Ticket channel](assets/ticket.png) |

| Deal log | Leaderboard |
|---|---|
| ![Deal log](assets/deal-log.png) | ![Leaderboard](assets/leaderboard.png) |

> If an image shows as broken, the screenshot hasn't been added yet.

---

## Features

- **Crix-style panels** with a logo, category titles and fixed INR rates
- **Exchange panel** with a dropdown for enabled exchange types
  (INR → Crypto, Crypto → INR, Crypto → Crypto disabled by default)
- **Two-step picker**: what you send, then what you receive
- **Details form** (modal) with amount validation and a configurable minimum
- **Automatic calculation** based on configurable rates / fees (no external API)
- **Private ticket channels** with clean names (`inr-crypto-0001`) and permission
  overwrites for the client, staff roles, managers and the bot
- **Claim / Req MM / Close** buttons
  - atomic claim so two staff can't claim the same ticket
  - middleman requests add middleman roles to the channel
  - only the claimer (or a manager) can complete a deal
- **Deal logs** posted to a staff channel, with staff tax recorded per deal
- **HTML transcripts** saved to a channel and DM'd to the client on close
- **Leaderboards** for customers (by volume) and staff (by volume), plus a
  monthly `,clb`, leaderboard reset and manual stat adjustments
- **Profiles** with rank, volume, all-time stats, handled deals and vouches
- **Vouch format** command (`,v`) and rep command (`,e`)
- **Staff tax** tracking: `,mytax`, `,stafffees`, `,cleartax`
- **Support tickets** and **staff applications** with their own panels
  (applications get Accept / Deny decisions)
- **Prefix and slash commands** — every command works as `,command` and `/command`
- **Persistent views** — buttons and dropdowns keep working after a restart

---

## How it works

```
Panel message (dropdown)
   └─ user picks: INR to Crypto / Crypto to INR / Crypto to Crypto
        └─ ephemeral picker: what you SEND + what you RECEIVE
             └─ "Continue" opens a form (amount)
                  └─ bot calculates the INR amount / fee
                       └─ bot creates a private ticket channel
                            └─ staff: Claim -> handle deal -> Complete & close
                                 └─ bot logs the deal, tax and transcript
```

### Rates and amounts

| Type | Rate used | Calculation |
|---|---|---|
| INR → Crypto | `inr_to_crypto` (default 104 INR / $) | INR to pay = USD × rate |
| Crypto → INR | `crypto_to_inr` (default 102 INR / $) | INR received = USD × rate |
| Crypto → Crypto | `fee_crypto_to_crypto` (default 3%) | receive = USD − fee |

The bot works in **USD values**; the INR rate is only used to show the amount
to pay or receive. Rates are stored per server and can be changed live with
`,setrate`, `,setfee` and `,settax`.

---

## Project structure

| File | Purpose |
|---|---|
| `bot.py` | Starts the bot, loads cogs, syncs slash commands |
| `config.py` | Brand, prefix, rates, currencies, role kinds, vouch format |
| `database.py` | SQLite schema and helpers via `aiosqlite` |
| `utils/checks.py` | Role-kind checks, `require()` decorator, safe modals |
| `utils/calc.py` | Rate lookups and exchange calculations |
| `utils/confirm.py` | Reusable confirmation view |
| `utils/ticket_views.py` | Persistent ticket button views per ticket kind |
| `utils/tickets.py` | Ticket engine: create, claim, MM, complete, close |
| `utils/transcript.py` | Builds the HTML transcript |
| `cogs/setup_cog.py` | Server setup, roles, rates and tax commands |
| `cogs/exchange.py` | Exchange panel and ticket creation flow |
| `cogs/support.py` | Support and staff application panels |
| `cogs/ticket_commands.py` | `,claim`, `,uc`, `,close`, `,transcript`, `,v`, `,3p` |
| `cogs/stats.py` | Leaderboards, profiles, vouches and staff tax |
| `cogs/calculators.py` | `,calc`, `,rates`, `,help`, `,ping` |

```
exchange-bot/
├── .env                  # secrets (NOT committed)
├── .gitignore
├── requirements.txt
├── bot.py
├── config.py
├── database.py
├── utils/
│   ├── __init__.py
│   ├── checks.py
│   ├── calc.py
│   ├── confirm.py
│   ├── ticket_views.py
│   ├── tickets.py
│   └── transcript.py
└── cogs/
    ├── __init__.py
    ├── setup_cog.py
    ├── exchange.py
    ├── support.py
    ├── ticket_commands.py
    ├── stats.py
    └── calculators.py
```

---

## Prerequisites

- **Python 3.10+**
- A Discord server where you have admin rights (use a test server first)
- Developer Mode enabled in Discord to copy IDs

---

## Setup

### 1. Create the bot on Discord

1. Go to <https://discord.com/developers/applications> and click **New Application**.
2. Open **Bot**, click **Reset Token**, copy it and keep it secret.
3. Under **Privileged Gateway Intents**, enable **Message Content Intent**.
4. (Optional) Turn **Public Bot** off. Save changes.

### 2. Invite the bot

1. Go to **OAuth2 → URL Generator**.
2. **Scopes:** `bot` and `applications.commands`.
3. **Bot Permissions:** View Channels, Manage Channels, Send Messages,
   Embed Links, Attach Files, Read Message History, Mention Everyone.
4. Open the URL, pick your server and authorize.

### 3. Clone and install

```bash
git clone https://github.com/ayux07/discord-exchange-bot.git exchange-bot
cd exchange-bot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Configure `.env`

```env
DISCORD_TOKEN=your_bot_token_here
DEV_GUILD_ID=your_test_server_id_here
```

`DEV_GUILD_ID` makes slash commands appear instantly in that server. Remove it
in production (commands then sync globally, which can take up to an hour).

### 5. Run

```bash
python bot.py
```

---

## Configure the server

Create this structure (names are up to you):

```
📁 EXCHANGE
   #exchange           ← exchange panel
   #support            ← support panel
   #apply              ← staff application panel
📁 TICKETS             ← ticket channels are created here
📁 STAFF ONLY
   #deal-logs          ← completed deal logs
   #transcripts        ← closed ticket transcripts
```

Create roles such as **Exchanger**, **Support**, **Manager**, **Middleman**.

The bot's role must have View Channel, Manage Channels, Send Messages, Embed
Links, Attach Files and Read Message History in the ticket category. Move the
bot's role **above** the staff roles it needs to manage.

### Initial setup

```
,setup #TICKETS #deal-logs #transcripts
,addrole exchanger @Exchanger
,addrole support @Support
,addrole application @Owner
,addrole middleman @Middleman
,addrole manager @Manager
,roles
```

Then post the panels in their channels:

```
,exchangepanel
,supportpanel
,applypanel
```

### Optional branding

Drop a logo at `assets/logo.png`. It is used as the panel and ticket thumbnail.

---

## Commands

### Everyone

| Command | Description |
|---|---|
| `,calc <type> <amount_usd> <send> <receive>` | Calculate an exchange |
| `,rates` | Show current rates, fee and tax |
| `,lb [users\|staff]` | Leaderboard since the last reset |
| `,clb [users\|staff]` | Leaderboard for the current month |
| `,p [@user]` | Exchange profile |
| `,deals [@user]` | Last 10 completed deals |
| `,help` | List commands |
| `,ping` | Bot latency |

### Ticket commands

| Command | Description |
|---|---|
| `,claim` | Claim the current ticket |
| `,uc` / `,unclaim` | Unclaim the ticket |
| `,close` | Close (optionally complete) the ticket |
| `,transcript` | Generate an HTML transcript |
| `,v` | Generate a vouch message for the deal |
| `,3p @user` | Add/remove a third party in the ticket |

### Staff

| Command | Description |
|---|---|
| `,mytax` | Tax you currently owe |
| `,e @user [note]` | Add a vouch for a user |

### Managers

| Command | Description |
|---|---|
| `,exchangepanel`, `,supportpanel`, `,applypanel` | Post panels |
| `,setrate <type> <value>` | Set INR rate |
| `,setfee <percent>` | Set crypto-to-crypto fee |
| `,settax <percent>` | Set staff tax percent |
| `,stafffees` | Tax owed by all staff |
| `,cleartax @user` | Mark a staff member's tax as paid |
| `,addlb @user <deals> <volume>` | Add manual leaderboard stats |
| `,setlb @user <deals> <volume>` | Set a user's leaderboard totals |
| `,resetlb` | Start a new leaderboard (history kept) |

### Admins

| Command | Description |
|---|---|
| `,setup <category> <deal_logs> <transcripts>` | Store channels |
| `,addrole <kind> @role` | Give a role a permission kind |
| `,removerole <kind> @role` | Remove a role from a kind |
| `,roles` | Show configured roles |

---

## Configuration (`config.py`)

- `PREFIX` — command prefix (default `,`)
- `BRAND` — brand name on panels and embeds
- `EMBED_COLOR` — embed accent color
- `TIMEZONE` — timezone used in ticket footers
- `MIN_USD` — minimum exchange amount
- `DEFAULT_RATES`, `DEFAULT_C2C_FEE`, `DEFAULT_TAX_PERCENT` — defaults
- `EX_TYPES` — per-type labels, slugs and whether they are enabled
- `INR_METHODS` — payment methods (label → short code)
- `CRYPTOS` — supported coin symbols
- `ROLE_KINDS` — descriptions for role kinds
- `VOUCH_FORMAT` — template used by `,v`

Add a coin by adding its symbol to `CRYPTOS`. Add a payment method by adding a
`"Label": "CODE"` entry to `INR_METHODS`.

---

## Testing checklist

| # | Test | Expected result |
|---|---|---|
| 1 | `,exchangepanel` | Panel is posted |
| 2 | Pick **INR to Crypto**, choose UPI + USDT, Continue | Form opens |
| 3 | Type an invalid or too-small amount | Clear validation error |
| 4 | Submit a valid amount | Private ticket with calculated INR amount |
| 5 | Open a second exchange ticket | Refused: existing open ticket |
| 6 | Staff presses **Claim** | Claim succeeds; a second staff cannot claim |
| 7 | Press **Req MM** | Middleman roles are added and pinged |
| 8 | Press **Close → Deal completed** | Deal log posted, tax recorded, transcript sent |
| 9 | `,lb`, `,clb`, `,p`, `,deals` | The deal appears |
| 10 | `,mytax`, `,stafffees`, `,cleartax` | Tax tracking works |
| 11 | Restart the bot, use panel and ticket buttons | Everything still works |

---

## Deployment (24/7)

| Option | Notes |
|---|---|
| **VPS** (Hetzner, DigitalOcean, Contabo, Oracle free tier) | Best control |
| **Railway / Fly.io / Render** | Add a **persistent volume** for `exchange.db` |
| **Home PC / Raspberry Pi** | Free, but goes down with power/internet |

### VPS with systemd (Ubuntu)

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
git clone https://github.com/ayux07/discord-exchange-bot.git exchange-bot
cd exchange-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nano .env
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

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now exchange-bot
journalctl -u exchange-bot -f
```

**Back up `exchange.db` regularly** — it holds all tickets, deals and settings.

---

## Security & scam protection

- **Never commit `.env`.** If the token leaks, reset it immediately.
- Give the bot only the permissions it needs.
- Every staff action checks role kinds. Keep it that way for new buttons.
- Always use `?` placeholders in SQL; never build queries from user input.
- Protect your Discord and VPS accounts with 2FA.
- Staff never move funds outside the ticket channel or via DMs.
- Only accept payment from an account in the customer's own name.
- Confirm funds have settled before releasing crypto — screenshots can be faked.
- Crypto transfers are irreversible: double-check addresses and networks.
- Keep every transcript — they are evidence in a dispute.

### Legal note

Running an exchange service may carry legal obligations depending on your
country (AML/KYC, registration, taxes). This project is technical help, not
legal advice. Consult a qualified professional before operating commercially.

---

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `LoginFailure: Improper token` | Wrong/missing `DISCORD_TOKEN`. Reset it and update `.env`. |
| `PrivilegedIntentsRequired` | Enable **Message Content Intent**. |
| Slash commands don't appear | Set `DEV_GUILD_ID`; check the `applications.commands` scope; restart Discord. |
| Buttons stop working after restart | Ensure `timeout=None`, `custom_id`, and `bot.add_view(...)` in `cog_load`. |
| Cannot create ticket channel | Bot lacks **Manage Channels**, lacks a permission it grants, or the category is full. |
| Empty transcripts | Message Content Intent is off. |
| Rates look wrong | Use `,setrate`, `,setfee`, `,settax`. Existing tickets keep their original rate. |
| `no such column` | Old schema. Delete `exchange.db` in development. |

See `discord_exchange_bot_guide_v2.md` for the full step-by-step build guide.

---

## License

Licensed under the [MIT License](LICENSE) — free to use, modify and distribute.
Review the legal note above before operating a service commercially.
