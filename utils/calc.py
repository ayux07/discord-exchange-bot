from utils.rates import rates

def fmt_crypto(value: float) -> str:
    return f"{value:,.8f}".rstrip("0").rstrip(".")

async def calculate(ex_type: str, amount: float, method: str, crypto: str, fee_pct: float) -> dict:
    usdt_inr = await rates.price("USDT", "inr")
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
