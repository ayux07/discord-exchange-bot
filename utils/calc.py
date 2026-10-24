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
