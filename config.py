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
