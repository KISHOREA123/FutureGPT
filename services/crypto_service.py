"""
services/crypto_service.py — Fetches live crypto prices from CoinGecko.
Falls back to mock data when the API is unavailable or key is missing.
"""

import logging
import aiohttp

from config import settings

logger = logging.getLogger(__name__)

# Top coins to display on the price card
TOP_COINS = ["bitcoin", "ethereum", "binancecoin", "solana", "ripple"]
COIN_LABELS = {
    "bitcoin":     "Bitcoin (BTC)",
    "ethereum":    "Ethereum (ETH)",
    "binancecoin": "Binance Coin",
    "solana":      "Solana (SOL)",
    "ripple":      "XRP (XRP)",
}


async def fetch_prices() -> str:
    """Return a formatted price card string."""
    url = f"{settings.COINGECKO_BASE_URL}/simple/price"
    params = {
        "ids": ",".join(TOP_COINS),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    raise ValueError(f"CoinGecko returned HTTP {resp.status}")
                data: dict = await resp.json()

        lines = ["<b>📊 Live Crypto Prices (USD)</b>\n"]
        for coin_id in TOP_COINS:
            coin = data.get(coin_id, {})
            price  = coin.get("usd", 0)
            change = coin.get("usd_24h_change", 0)
            arrow  = "🟢" if change >= 0 else "🔴"
            label  = COIN_LABELS.get(coin_id, coin_id)
            lines.append(
                f"{arrow} <b>{label}</b>\n"
                f"   ${price:,.2f}  ({change:+.2f}%)\n"
            )

        lines.append("\n<i>Powered by CoinGecko · Updates every request</i>")
        return "\n".join(lines)

    except Exception as exc:
        logger.warning("Price fetch failed: %s — returning mock data", exc)
        return _mock_prices()


def _mock_prices() -> str:
    return (
        "<b>📊 Crypto Prices (Demo Data)</b>\n\n"
        "🟢 <b>Bitcoin (BTC)</b>\n   $67,420.00  (+2.34%)\n\n"
        "🟢 <b>Ethereum (ETH)</b>\n   $3,512.80  (+1.89%)\n\n"
        "🔴 <b>Binance Coin</b>\n   $574.30  (-0.45%)\n\n"
        "🟢 <b>Solana (SOL)</b>\n   $183.60  (+4.12%)\n\n"
        "🟢 <b>XRP (XRP)</b>\n   $0.548  (+0.77%)\n\n"
        "<i>⚠️ Live API unavailable — showing demo data</i>"
    )
