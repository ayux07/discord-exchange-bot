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
