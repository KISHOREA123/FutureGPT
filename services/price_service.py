"""
services/price_service.py — Real-time crypto prices via Binance public API.
"""

import logging
import aiohttp

logger = logging.getLogger(__name__)

BINANCE_BASE    = "https://api.binance.com/api/v3"
TICKER_24H      = f"{BINANCE_BASE}/ticker/24hr"
QUOTE_CURRENCY  = "USDT"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=8)

DASHBOARD_SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "XRP"]

COIN_META: dict[str, dict] = {
    "BTC":   {"icon": "",  "name": "Bitcoin"},
    "ETH":   {"icon": "",  "name": "Ethereum"},
    "BNB":   {"icon": "",  "name": "BNB"},
    "SOL":   {"icon": "",  "name": "Solana"},
    "XRP":   {"icon": "",  "name": "XRP"},
    "ADA":   {"icon": "",  "name": "Cardano"},
    "DOT":   {"icon": "",  "name": "Polkadot"},
    "DOGE":  {"icon": "",  "name": "Dogecoin"},
    "AVAX":  {"icon": "", "name": "Avalanche"},
    "LTC":   {"icon": "",  "name": "Litecoin"},
    "LINK":  {"icon": "", "name": "Chainlink"},
    "UNI":   {"icon": "", "name": "Uniswap"},
    "ATOM":  {"icon": "", "name": "Cosmos"},
    "NEAR":  {"icon": "",  "name": "NEAR"},
    "TON":   {"icon": "", "name": "Toncoin"},
    "TRX":   {"icon": "", "name": "TRON"},
    "APT":   {"icon": "",  "name": "Aptos"},
    "SUI":   {"icon": "", "name": "Sui"},
    "OP":    {"icon": "", "name": "Optimism"},
    "ARB":   {"icon": "", "name": "Arbitrum"},
    "PEPE":  {"icon": "", "name": "Pepe"},
    "SHIB":  {"icon": "", "name": "Shiba Inu"},
    "POL":   {"icon": "",  "name": "Polygon"},
    "FLOKI": {"icon": "", "name": "Floki"},
    "BONK":  {"icon": "", "name": "Bonk"},
    "NOT":   {"icon": "", "name": "Notcoin"},
    "GALA":  {"icon": "", "name": "Gala"},
    "SAND":  {"icon": "", "name": "The Sandbox"},
    "CHZ":   {"icon": "", "name": "Chiliz"},
    "BRETT": {"icon": "", "name": "Brett"},
    "WIF":   {"icon": "", "name": "dogwifhat"},
    "KAS":   {"icon": "", "name": "Kaspa"},
    "INJ":   {"icon": "", "name": "Injective"},
    "FET":   {"icon": "", "name": "Fetch.ai"},
    "RENDER":{"icon": "", "name": "Render"},
    "IMX":   {"icon": "", "name": "Immutable"},
    "GRT":   {"icon": "", "name": "The Graph"},
    "AAVE":  {"icon": "", "name": "Aave"},
    "MKR":   {"icon": "", "name": "Maker"},
    "FIL":   {"icon": "", "name": "Filecoin"},
    "ICP":   {"icon": "",  "name": "Internet Computer"},
    "VET":   {"icon": "", "name": "VeChain"},
    "ALGO":  {"icon": "",  "name": "Algorand"},
    "HBAR":  {"icon": "",  "name": "Hedera"},
    "XLM":   {"icon": "", "name": "Stellar"},
    "ETC":   {"icon": "", "name": "Ethereum Classic"},
    "MANA":  {"icon": "", "name": "Decentraland"},
    "AXS":   {"icon": "", "name": "Axie Infinity"},
    "CRV":   {"icon": "", "name": "Curve"},
    "LDO":   {"icon": "", "name": "Lido DAO"},
    "RNDR":  {"icon": "", "name": "Render"},
    "ENS":   {"icon": "", "name": "Ethereum Name Service"},
    "SNX":   {"icon": "", "name": "Synthetix"},
    "CAKE":  {"icon": "", "name": "PancakeSwap"},
    "ZEC":   {"icon": "", "name": "Zcash"},
    "DASH":  {"icon": "", "name": "Dash"},
    "XMR":   {"icon": "", "name": "Monero"},
    "EOS":   {"icon": "", "name": "EOS"},
    "XTZ":   {"icon": "", "name": "Tezos"},
    "THETA": {"icon": "", "name": "Theta"},
    "RUNE":  {"icon": "", "name": "THORChain"},
    "EGLD":  {"icon": "", "name": "MultiversX"},
}

VALID_SYMBOLS: set[str] = set(COIN_META.keys())


class InvalidSymbolError(ValueError):
    """Raised when the user supplies an unknown / unsupported ticker."""


async def get_single_price(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if symbol not in VALID_SYMBOLS:
        raise InvalidSymbolError(symbol)

    pair = f"{symbol}{QUOTE_CURRENCY}"
    data = await _fetch_ticker(pair)

    price    = float(data["lastPrice"])
    change   = float(data["priceChangePercent"])
    high_24h = float(data["highPrice"])
    low_24h  = float(data["lowPrice"])
    volume   = float(data["quoteVolume"])

    trend = "📈" if change >= 0 else "📉"
    dot   = "🟢" if change >= 0 else "🔴"
    meta  = COIN_META.get(symbol, {"icon": "🪙", "name": symbol})

    return (
        f"📊 <b>{meta['icon']} {meta['name']} ({symbol}/USDT)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Price</b>      <code>${price:>12,.4f}</code>\n"
        f"{trend} <b>24h Change</b> <code>{change:>+10.2f}%</code>  {dot}\n"
        f"⬆️ <b>24h High</b>   <code>${high_24h:>12,.4f}</code>\n"
        f"⬇️ <b>24h Low</b>    <code>${low_24h:>12,.4f}</code>\n"
        f"📦 <b>Volume</b>     <code>${volume:>12,.0f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>🔄 Live · Binance · {pair}</i>"
    )


async def get_price_dashboard() -> str:
    pairs  = [f"{s}{QUOTE_CURRENCY}" for s in DASHBOARD_SYMBOLS]
    quoted = ",".join(f'"{p}"' for p in pairs)
    params = [("symbols", f"[{quoted}]")]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(TICKER_24H, params=params, timeout=REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                tickers: list[dict] = await resp.json()

        by_symbol = {t["symbol"]: t for t in tickers}
        lines = ["<b>📊 Live Crypto Dashboard</b>  <i>(Binance)</i>\n"]

        for sym in DASHBOARD_SYMBOLS:
            pair = f"{sym}{QUOTE_CURRENCY}"
            t    = by_symbol.get(pair)
            if not t:
                continue
            price  = float(t["lastPrice"])
            change = float(t["priceChangePercent"])
            dot    = "🟢" if change >= 0 else "🔴"
            meta   = COIN_META.get(sym, {"icon": "🪙", "name": sym})
            lines.append(
                f"{dot} <b>{meta['icon']} {sym}</b>  "
                f"<code>${price:,.2f}</code>  "
                f"<i>({change:+.2f}%)</i>"
            )

        lines.append(
            "\n<i>💡 Use /price &lt;symbol&gt; for full details\n"
            "e.g. /price BTC  ·  /price ETH  ·  /price SOL</i>"
        )
        return "\n".join(lines)

    except Exception as exc:
        logger.warning("Dashboard fetch failed: %s", exc)
        return _dashboard_fallback()


async def get_top_movers() -> dict:
    """
    Fetch top 5 gainers and top 5 losers from all USDT pairs on Binance.
    Returns {"gainers": [...], "losers": [...]}
    Each item: {"symbol": "BTC", "price": 67000.0, "change": 5.2}
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(TICKER_24H, timeout=REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                all_tickers: list[dict] = await resp.json()

        # Filter to USDT pairs only, exclude stablecoins and leveraged tokens
        EXCLUDE = {"USDC", "BUSD", "TUSD", "USDP", "DAI", "FDUSD", "USDD",
                   "EUR", "GBP", "BRL", "TRY", "AUD"}
        usdt_pairs = []
        for t in all_tickers:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            base = sym[:-4]
            # Skip stablecoins, leveraged tokens (contain digits or UP/DOWN/BULL/BEAR)
            if base in EXCLUDE:
                continue
            if any(x in base for x in ["UP", "DOWN", "BULL", "BEAR", "3L", "3S"]):
                continue
            try:
                change = float(t["priceChangePercent"])
                price  = float(t["lastPrice"])
                volume = float(t.get("quoteVolume", 0))
                # Minimum $100k daily volume to filter noise
                if volume < 100_000:
                    continue
                usdt_pairs.append({
                    "symbol": base,
                    "price":  price,
                    "change": change,
                    "volume": volume,
                })
            except (ValueError, KeyError):
                continue

        usdt_pairs.sort(key=lambda x: x["change"])
        losers  = usdt_pairs[:5]
        gainers = list(reversed(usdt_pairs[-5:]))

        return {"gainers": gainers, "losers": losers}

    except Exception as exc:
        logger.error("Top movers fetch failed: %s", exc)
        return {"gainers": [], "losers": []}


def format_top_movers(data: dict) -> str:
    """Format gainers + losers into a Telegram HTML card."""
    gainers = data.get("gainers", [])
    losers  = data.get("losers", [])

    lines = ["<b>🔥 Top Movers — 24H</b>  <i>(Binance · All USDT Pairs)</i>\n"]

    lines.append("🟢 <b>Top Gainers</b>")
    if gainers:
        for i, c in enumerate(gainers, 1):
            lines.append(
                f"  {i}. <b>{c['symbol']}</b>  "
                f"<code>${c['price']:,.4f}</code>  "
                f"<b>+{c['change']:.2f}%</b> 🚀"
            )
    else:
        lines.append("  <i>Data unavailable</i>")

    lines.append("")
    lines.append("🔴 <b>Top Losers</b>")
    if losers:
        for i, c in enumerate(losers, 1):
            lines.append(
                f"  {i}. <b>{c['symbol']}</b>  "
                f"<code>${c['price']:,.4f}</code>  "
                f"<b>{c['change']:.2f}%</b> 📉"
            )
    else:
        lines.append("  <i>Data unavailable</i>")

    lines.append(
        "\n<i>🔄 Live · Binance · Min $100k daily volume\n"
        "⚠️ Informational only — not financial advice</i>"
    )
    return "\n".join(lines)


def invalid_symbol_message(symbol: str) -> str:
    popular = ", ".join(DASHBOARD_SYMBOLS)
    return (
        f"⚠️ <b>Invalid symbol:</b> <code>{symbol}</code>\n\n"
        f"Try one of the popular coins:\n<code>{popular}</code>\n\n"
        f"<i>Usage: /price BTC  ·  /price ETH  ·  /price SOL</i>"
    )


async def _fetch_ticker(pair: str) -> dict:
    params = {"symbol": pair}
    async with aiohttp.ClientSession() as session:
        async with session.get(TICKER_24H, params=params, timeout=REQUEST_TIMEOUT) as resp:
            if resp.status == 400:
                raise InvalidSymbolError(pair)
            resp.raise_for_status()
            return await resp.json()


def _dashboard_fallback() -> str:
    return (
        "<b>📊 Crypto Prices</b>  <i>(Demo — API unreachable)</i>\n\n"
        "🟢 <b>BTC</b>  <code>$67,420.00</code>  <i>(+2.34%)</i>\n"
        "🟢 <b>ETH</b>  <code>$ 3,512.80</code>  <i>(+1.89%)</i>\n"
        "🔴 <b>BNB</b>  <code>$   574.30</code>  <i>(-0.45%)</i>\n"
        "🟢 <b>SOL</b>  <code>$   183.60</code>  <i>(+4.12%)</i>\n"
        "🟢 <b>XRP</b>  <code>$     0.55</code>  <i>(+0.77%)</i>\n\n"
        "<i>⚠️ Could not reach Binance — showing demo data.</i>"
    )