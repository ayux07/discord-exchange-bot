BRAND = "Atrix Exchange"
EMBED_COLOR = 0x5865F2

EX_TYPES = {
    "inr_to_crypto": {
        "label": "INR to Crypto",
        "slug": "inr-crypto",
        "fee": 6.0,
        "min": 100,
        "unit": "INR",
    },
    "crypto_to_inr": {
        "label": "Crypto to INR",
        "slug": "crypto-inr",
        "fee": 5.0,
        "min": 100,
        "unit": "INR",
    },
    "crypto_to_crypto": {
        "label": "Crypto to Crypto",
        "slug": "crypto-crypto",
        "fee": 3.0,
        "min": 10,
        "unit": "USD",
    },
}

INR_METHODS = [
    "UPI", "Bank Transfer", "IMPS", "Omnicard", "Mobikwik",
    "Google Pay", "PhonePe", "Paytm", "Fampay",
]

CRYPTOS = ["LTC", "USDT", "BTC", "ETH", "TRX"]
