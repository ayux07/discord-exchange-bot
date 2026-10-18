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
CACHE_SECONDS = 60
MAX_STALE_SECONDS = 15 * 60

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
                if self._data is None or age > MAX_STALE_SECONDS:
                    raise
        return float(self._data[COIN_IDS[symbol]][currency.lower()])

rates = RateService()
