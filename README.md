# Discord Exchange Ticket Bot

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![discord.py](https://img.shields.io/badge/discord.py-2.4%2B-5865F2.svg)](https://discordpy.readthedocs.io/)
[![aiosqlite](https://img.shields.io/badge/storage-SQLite-orange.svg)](https://aiosqlite.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-working-brightgreen.svg)](https://github.com/ayux07/discord-exchange-bot)

A complete **INR ↔ Crypto exchange ticket bot** built with [`discord.py`](https://discordpy.readthedocs.io/).

It automates the *workflow* of running a peer-to-peer crypto exchange on Discord:
dropdown panels, private ticket channels, live rate calculation, staff
claim/complete/close buttons, HTML transcripts, deal logs, leaderboards,
user profiles, support tickets and staff applications.

> The actual money and crypto transfers are done **manually by your staff**.
> This bot handles the workflow, calculations, logging and statistics.

---

## Screenshots

Add your own screenshots by dropping images into `assets/`, then link them here.

| Exchange panel | Ticket channel |
|---|---|
| ![Exchange panel](assets/panel.png) | ![Ticket channel](assets/ticket.png) |

| Deal log | Leaderboard |
|---|---|
| ![Deal log](assets/deal-log.png) | ![Leaderboard](assets/leaderboard.png) |

> **Note:** if an image shows as broken, it just means the screenshot hasn't
> been added yet.

---

## Features

- **Exchange panel** with a dropdown for 3 exchange types
  (INR → Crypto, Crypto → INR, Crypto → Crypto)
- **Payment / coin pickers** (UPI, Bank Transfer, IMPS, UPI apps, … and BTC/ETH/LTC/USDT/TRX)
- **Details form** (modal) that validates the amount and minimums
- **Live rates** from the CoinGecko API, cached for 60 seconds
- **Automatic fee + receive amount calculation** per exchange type
- **Private ticket channels** visible only to the customer, staff and the bot
- **Claim / Complete Deal / Close** buttons
  - atomic `Claim` so two staff can't claim the same ticket
  - only the staff member who claimed a ticket can complete it
  - deal log posted to a staff channel on completion
- **HTML transcripts** saved to a channel and DM'd to the customer on close
- **`/leaderboard`** (top customers by volume, top staff by deals handled)
- **`/profile`** (completed deals, total volume, last deal)
- **Support tickets** with their own panel and buttons
- **Staff applications** with Accept / Deny buttons
- **Persistent views** — buttons and dropdowns keep working after a restart

---

## How it works

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

### Amounts, fees and minimums

| Type | "Amount" the user types | Fee applied to | User receives |
|---|---|---|---|
| INR to Crypto | INR they send | INR amount | (amount − fee) ÷ coin price in INR |
| Crypto to INR | INR **value** of crypto sent | INR amount | amount − fee, in INR |
| Crypto to Crypto | USD value of what they send | USD amount | (amount − fee) ÷ receive coin price in USD |

Fees and minimums are configured in `config.py`:

| Type | Fee (default) | Minimum (default) |
|---|---|---|
| INR → Crypto | 6% | 100 INR |
| Crypto → INR | 5% | 100 INR |
| Crypto → Crypto | 3% | 10 USD |

---

## Project structure

| File | Purpose |
|---|---|
| `bot.py` | Starts the bot, loads cogs, syncs slash commands |
| `config.py` | Brand name, fees, minimums, payment methods, coins |
| `database.py` | SQLite storage (settings, tickets) via `aiosqlite` |
| `utils/checks.py` | `is_staff()` helper |
| `utils/rates.py` | Live prices from CoinGecko, with caching + stale guard |
| `utils/calc.py` | Fee and amount calculation for the 3 exchange types |
| `utils/transcript.py` | Turns a channel's history into an HTML file |
| `utils/tickets.py` | Shared logic: create ticket channel, claim, close |
| `cogs/setup_cog.py` | `/setup` — stores roles and channels per server |
| `cogs/exchange.py` | Exchange panel and the full ticket workflow |
| `cogs/stats.py` | `/leaderboard` and `/profile` |
| `cogs/support.py` | Support tickets and staff applications |

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

---

## Prerequisites

- **Python 3.10+**
- A Discord account with a server where you have admin rights
  (create a **separate test server** first)
- Developer Mode enabled in Discord
  (User Settings → Advanced → Developer Mode) to copy IDs

---

## Setup

### 1. Create the bot on Discord

1. Go to <https://discord.com/developers/applications> and click **New Application**.
2. Open **Bot** in the sidebar.
3. Click **Reset Token**, copy it and keep it secret.
4. Under **Privileged Gateway Intents**, enable **Message Content Intent**.
5. (Optional) Turn **Public Bot** off. Save changes.

### 2. Invite the bot to your server

1. Go to **OAuth2 → URL Generator**.
2. **Scopes:** `bot` and `applications.commands`.
3. **Bot Permissions** (do **not** give Administrator):
   - View Channels
   - Manage Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Mention Everyone (optional)
4. Open the generated URL, pick your server, click **Authorize**.

### 3. Clone and install

```bash
git clone https://github.com/ayux07/discord-exchange-bot.git exchange-bot
cd exchange-bot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Configure `.env`

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_bot_token_here
DEV_GUILD_ID=your_test_server_id_here
```

`DEV_GUILD_ID` makes slash commands appear **instantly** in your test server.
Right-click the server icon → Copy Server ID. Remove it in production.

### 5. Run

```bash
python bot.py
```

You should see `Logged in as ... (ID: ...)`.

---

## Configure the server

Create this structure in your Discord server (names are up to you):

```
📁 EXCHANGE            ← put the panels here
   #exchange           ← public: exchange panel
   #support            ← public: support panel
   #apply              ← public: staff application panel
📁 TICKETS             ← bot creates ticket channels here
📁 STAFF ONLY
   #deal-logs          ← only staff can see
   #transcripts        ← only staff can see
   #applications       ← only staff can see
```

Also create a **Staff** role.

**Permission rule:** the bot's role must have View Channel, Send Messages,
Read Message History, Attach Files and Embed Links (server-wide or in the
TICKETS category), because a bot can only grant permissions it has itself.
Move the bot's role **above** the Staff role in Server Settings → Roles.

Then run:

```
/setup staff_role:@Staff ticket_category:TICKETS deal_log_channel:#deal-logs transcript_channel:#transcripts applications_channel:#applications
```

And post the panels:

- in `#exchange` → `/exchange_panel`
- in `#support`  → `/support_panel`
- in `#apply`    → `/apply_panel`

---

## Commands

| Command | Who | Description |
|---|---|---|
| `/setup` | Admin | Store staff role and channels for this server |
| `/exchange_panel` | Admin | Post the exchange panel in the current channel |
| `/support_panel` | Admin | Post the support panel |
| `/apply_panel` | Admin | Post the staff application panel |
| `/leaderboard` | Everyone | Top customers (by volume) or top staff (deals handled) |
| `/profile` | Everyone | Exchange stats for a user |

---

## Configuration (`config.py`)

Everything you might want to tweak lives in `config.py`:

- `BRAND` — your brand name shown on panels and embeds
- `EMBED_COLOR` — embed accent color
- `EX_TYPES` — per-type label, slug, fee (%) and minimum
- `INR_METHODS` — payment methods shown in the picker
- `CRYPTOS` — supported coins (symbols must exist in `utils/rates.py` `COIN_IDS`)

To add a coin:

1. Add the symbol to `CRYPTOS` in `config.py`.
2. Add its CoinGecko id to `COIN_IDS` in `utils/rates.py`.

---

## Testing checklist

Use a second Discord account (or a friend) as the customer.

| # | Test | Expected result |
|---|---|---|
| 1 | Pick **INR to Crypto** | Ephemeral picker with two dropdowns |
| 2 | Press Continue without choosing | "Please choose both options first." |
| 3 | Choose UPI + USDT, Continue | Form opens |
| 4 | Type `abc` as amount | "Amount must be a number." |
| 5 | Type `10` | Minimum error |
| 6 | Type `1000` + wallet address | Ticket channel + embed with fee and receive amount |
| 7 | Pick an exchange type again | "You already have an open ticket" |
| 8 | Customer presses **Claim** | "Only staff can claim tickets." |
| 9 | Staff presses **Claim** | Button disables, claim message appears |
| 10 | Different staff presses **Complete Deal** | Refused (only the claimer can) |
| 11 | Claimer presses **Complete Deal** | Deal Logged embed in `#deal-logs` |
| 12 | Press **Close** → confirm | Transcript saved, DM to user, channel deleted after 5s |
| 13 | `/leaderboard` and `/profile` | The deal shows up |
| 14 | Restart the bot, then use panel + ticket buttons | Everything still works |
| 15 | Crypto to Crypto with the same coin both sides | Refused |

---

## Deployment (24/7)

The bot only runs while the Python process runs. Options:

| Option | Notes |
|---|---|
| **VPS** (Hetzner, DigitalOcean, Contabo, Oracle free tier) | Best control, ~₹300+/month |
| **Railway / Fly.io / Render** | Easy deploys. Add a **persistent volume** for `exchange.db`, or data is lost on redeploy |
| **Home PC / Raspberry Pi** | Free, but goes down when power/internet does |

### VPS with systemd (Ubuntu)

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
git clone https://github.com/ayux07/discord-exchange-bot.git exchange-bot
cd exchange-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nano .env                      # add DISCORD_TOKEN (no DEV_GUILD_ID in production)
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

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now exchange-bot
sudo systemctl status exchange-bot
journalctl -u exchange-bot -f      # live logs
```

**Back up `exchange.db` regularly** (e.g. a daily cron job). It holds all deal history.

---

## Security & scam protection

### Bot security

- **Never commit `.env`.** If the token leaks, click Reset Token immediately.
- Give the bot only the permissions listed above, **not Administrator**.
- All staff actions check `is_staff()`. Keep it that way for new buttons.
- Always use `?` placeholders in SQL. Never build queries from user input.
- Protect your server and any VPS accounts with 2FA.

### Operational rules for staff (strongly recommended)

P2P exchange servers are common targets for scammers and chargeback fraud:

- Staff **never** move funds outside the ticket channel, and never via DMs.
- Only accept payment **from an account in the customer's own name**.
- Confirm funds have **actually settled** before releasing crypto — screenshots can be faked.
- Crypto transfers are irreversible: double-check addresses and networks
  (e.g. USDT TRC20 vs BEP20).
- Start with low limits for new customers.
- Keep every transcript — they are your evidence in a dispute.
- Never share private keys, seed phrases or login codes.

### Legal note

Running an exchange service may carry legal obligations depending on your
country (AML/KYC, registration, taxes). This project is technical help, not
legal advice. Consult a qualified professional before operating commercially.

---

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `LoginFailure: Improper token` | Wrong/missing `DISCORD_TOKEN`. Reset token, update `.env`. |
| `PrivilegedIntentsRequired` | Enable **Message Content Intent** in the Developer Portal → Bot. |
| Slash commands don't appear | Set `DEV_GUILD_ID` for instant sync; check the bot was invited with the `applications.commands` scope; restart Discord (Ctrl+R). |
| "This interaction failed" | Took longer than 3s to respond — call `await interaction.response.defer()` first. |
| Buttons stop working after restart | View missing `timeout=None`, a `custom_id`, or `bot.add_view(...)` in `cog_load`. |
| "I could not create the ticket channel" | Bot lacks **Manage Channels**, lacks a permission it tries to grant, or the category is full (50 channels). |
| Transcript messages are empty | Message Content Intent off in code or portal. |
| Staff role not pinged | Role not mentionable and bot lacks **Mention Everyone**. |
| Rates fail ("Could not fetch live rates") | CoinGecko rate limit or network issue. Wait a minute. |
| `ModuleNotFoundError: No module named 'utils'` | Run `python bot.py` from the project folder; ensure `utils/__init__.py` exists. |
| `sqlite3.OperationalError: no such column` | Schema changed after DB creation. Delete `exchange.db` (dev only) or `ALTER TABLE`. |
| Dropdown shows the old choice | Ensure the panel message edit at the end of `ExchangeTypeSelect.callback` is present. |
| Two staff claim the same ticket | Keep the `claimed_by IS NULL` condition in the claim SQL. |

See `discord_exchange_bot_guide.md` for the full step-by-step build guide.

---

## License

Licensed under the [MIT License](LICENSE) — free to use, modify and distribute.
Review the legal note above before operating a service commercially.
