"""
services/news_service.py — Coin-specific and general crypto news.

Source priority (all free-tier / no key required):
  1. CryptoPanic public feed (no key needed for public posts)
  2. CoinGecko news endpoint  (completely free, no key)
  3. Curated demo headlines  (always available as final fallback)

Supports:
  • get_general_news()          → top 5 hot headlines (📰 News button)
  • get_coin_news(symbol)       → top 5 headlines filtered for a coin
  • coin_news_not_found(symbol) → formatted error card for bad symbols

Both functions return ready-to-send Telegram HTML strings.
Coin filtering uses CryptoPanic's currencies param when a key is present,
and client-side keyword matching on the free public feed otherwise.
"""

import logging
import html
import aiohttp
from datetime import datetime, timezone

from config import settings
from services.price_service import COIN_META, VALID_SYMBOLS

logger = logging.getLogger(__name__)

# ── API endpoints ─────────────────────────────────────────────────────────────

CRYPTOPANIC_URL  = "https://cryptopanic.com/api/v1/posts/"
COINGECKO_NEWS   = "https://api.coingecko.com/api/v3/news"
REQUEST_TIMEOUT  = aiohttp.ClientTimeout(total=10)
MAX_HEADLINES    = 5     # shown per card (3–5 per spec)


# ── Coin name aliases for keyword matching ─────────────────────────────────────
# Maps ticker → list of search terms (all lowercase)

_COIN_KEYWORDS: dict[str, list[str]] = {
    "BTC":  ["bitcoin", "btc", "satoshi"],
    "ETH":  ["ethereum", "eth", "ether", "vitalik"],
    "BNB":  ["bnb", "binance coin", "binance"],
    "SOL":  ["solana", "sol"],
    "XRP":  ["xrp", "ripple"],
    "ADA":  ["cardano", "ada"],
    "DOT":  ["polkadot", "dot"],
    "DOGE": ["dogecoin", "doge"],
    "MATIC":["polygon", "matic"],
    "AVAX": ["avalanche", "avax"],
    "LTC":  ["litecoin", "ltc"],
    "LINK": ["chainlink", "link"],
    "UNI":  ["uniswap", "uni"],
    "ATOM": ["cosmos", "atom"],
    "NEAR": ["near protocol", "near"],
    "TRX":  ["tron", "trx"],
    "ARB":  ["arbitrum", "arb"],
    "OP":   ["optimism", "op"],
    "APT":  ["aptos", "apt"],
    "SUI":  ["sui"],
    "PEPE": ["pepe"],
    "SHIB": ["shiba", "shib"],
}


# ── Public API ────────────────────────────────────────────────────────────────

async def get_general_news() -> str:
    """
    Fetch top-5 hot crypto headlines (no coin filter).
    Used by the 📰 News button and bare /news command.
    """
    logger.info("Fetching general crypto news")

    # Try CryptoPanic first (with or without key)
    result = await _cryptopanic_general()
    if result:
        return result

    # Fall back to CoinGecko
    result = await _coingecko_news()
    if result:
        return result

    # Final fallback: demo headlines
    logger.info("All news sources failed — using demo data")
    return _demo_general()


async def get_coin_news(symbol: str) -> str:
    """
    Fetch top-5 headlines specifically about `symbol`.

    Args:
        symbol: Uppercase ticker, e.g. "BTC". Must be in VALID_SYMBOLS.

    Returns:
        Formatted HTML Telegram card.
    """
    symbol = symbol.upper().strip()
    meta   = COIN_META.get(symbol, {"icon": "🪙", "name": symbol})
    logger.info("Fetching news for %s", symbol)

    # Try CryptoPanic with currency filter if key available
    if settings.NEWS_API_KEY:
        result = await _cryptopanic_coin(symbol, meta)
        if result:
            return result

    # Try CryptoPanic public feed + client-side filter
    result = await _cryptopanic_coin_public(symbol, meta)
    if result:
        return result

    # Fall back to CoinGecko + keyword filter
    result = await _coingecko_coin_news(symbol, meta)
    if result:
        return result

    # Final fallback: curated demo headlines for the coin
    logger.info("All sources failed for %s — using demo", symbol)
    return _demo_coin(symbol, meta)


def coin_news_not_found(symbol: str) -> str:
    """Error card for unrecognised tickers."""
    from services.price_service import DASHBOARD_SYMBOLS
    popular = "  ".join(f"<code>{s}</code>" for s in DASHBOARD_SYMBOLS)
    return (
        f"⚠️ <b>Unknown symbol:</b> <code>{symbol}</code>\n\n"
        f"Try one of these:\n{popular}\n\n"
        f"<i>Usage: /news BTC  ·  /news ETH  ·  /news SOL</i>"
    )


# ── CryptoPanic fetchers ──────────────────────────────────────────────────────

async def _cryptopanic_general() -> str | None:
    """Hot general news from CryptoPanic (public or authenticated)."""
    params: dict = {
        "public": "true",
        "kind":   "news",
        "filter": "hot",
    }
    if settings.NEWS_API_KEY:
        params["auth_token"] = settings.NEWS_API_KEY

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                CRYPTOPANIC_URL, params=params, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    logger.debug("CryptoPanic general: HTTP %s", resp.status)
                    return None
                data = await resp.json()

        items = data.get("results", [])[:MAX_HEADLINES]
        if not items:
            return None

        return _format_card(
            title="📰 Crypto News — Hot Stories",
            items=_extract_items(items),
            source="CryptoPanic",
            coin=None,
        )

    except Exception as exc:
        logger.debug("CryptoPanic general fetch error: %s", exc)
        return None


async def _cryptopanic_coin(symbol: str, meta: dict) -> str | None:
    """Coin-specific news via CryptoPanic currency filter (requires API key)."""
    params = {
        "auth_token": settings.NEWS_API_KEY,
        "public":     "true",
        "kind":       "news",
        "currencies": symbol,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                CRYPTOPANIC_URL, params=params, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        items = data.get("results", [])[:MAX_HEADLINES]
        if not items:
            return None

        return _format_card(
            title=f"📰 {meta['icon']} {meta['name']} News",
            items=_extract_items(items),
            source="CryptoPanic",
            coin=symbol,
        )

    except Exception as exc:
        logger.debug("CryptoPanic coin fetch error for %s: %s", symbol, exc)
        return None


async def _cryptopanic_coin_public(symbol: str, meta: dict) -> str | None:
    """CryptoPanic public feed + client-side keyword filtering (no API key)."""
    keywords = _COIN_KEYWORDS.get(symbol, [symbol.lower()])
    params   = {"public": "true", "kind": "news", "filter": "hot"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                CRYPTOPANIC_URL, params=params, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        all_items = data.get("results", [])
        matched   = _keyword_filter(all_items, keywords, max_items=MAX_HEADLINES)
        if not matched:
            return None

        return _format_card(
            title=f"📰 {meta['icon']} {meta['name']} News",
            items=_extract_items(matched),
            source="CryptoPanic",
            coin=symbol,
        )

    except Exception as exc:
        logger.debug("CryptoPanic public coin filter error: %s", exc)
        return None


# ── CoinGecko fetchers ────────────────────────────────────────────────────────

async def _coingecko_news() -> str | None:
    """General news from CoinGecko free API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                COINGECKO_NEWS, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    logger.debug("CoinGecko news: HTTP %s", resp.status)
                    return None
                data = await resp.json()

        items = data.get("data", [])[:MAX_HEADLINES]
        if not items:
            return None

        extracted = [
            {
                "title": _clean(item.get("title", "No title")),
                "url":   item.get("url", "#"),
            }
            for item in items
        ]
        return _format_card(
            title="📰 Crypto News — Latest",
            items=extracted,
            source="CoinGecko",
            coin=None,
        )

    except Exception as exc:
        logger.debug("CoinGecko news error: %s", exc)
        return None


async def _coingecko_coin_news(symbol: str, meta: dict) -> str | None:
    """CoinGecko general news + client-side keyword filter for a coin."""
    keywords = _COIN_KEYWORDS.get(symbol, [symbol.lower()])

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                COINGECKO_NEWS, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        all_items = data.get("data", [])

        # Filter by keywords in title
        matched = [
            {"title": _clean(item.get("title", "")), "url": item.get("url", "#")}
            for item in all_items
            if any(kw in item.get("title", "").lower() for kw in keywords)
        ][:MAX_HEADLINES]

        if not matched:
            return None

        return _format_card(
            title=f"📰 {meta['icon']} {meta['name']} News",
            items=matched,
            source="CoinGecko",
            coin=symbol,
        )

    except Exception as exc:
        logger.debug("CoinGecko coin news error: %s", exc)
        return None


# ── Formatting ────────────────────────────────────────────────────────────────

def _format_card(
    title: str,
    items: list[dict],
    source: str,
    coin: str | None,
) -> str:
    """
    Render a clean numbered news card.

    Output example:
      📰 BTC News
      ━━━━━━━━━━━━━━━━━━━━
      1. <a href="...">ETF approval speculation rises</a>
      2. <a href="...">Market sees slight correction</a>
      3. <a href="...">Whale accumulation increases</a>
      ━━━━━━━━━━━━━━━━━━━━
      🕐 Updated just now  ·  Source  ·  /news BTC
    """
    lines = [f"<b>{title}</b>", "━━━━━━━━━━━━━━━━━━━━"]

    for i, item in enumerate(items, 1):
        clean_title = item["title"]
        url         = item.get("url", "#")
        if url and url != "#":
            lines.append(f"{i}. <a href='{url}'>{clean_title}</a>")
        else:
            lines.append(f"{i}. {clean_title}")

    lines.append("━━━━━━━━━━━━━━━━━━━━")

    # Footer: timestamp + source + refresh hint
    now_str  = _now_label()
    cmd_hint = f"/news {coin}" if coin else "/news"
    lines.append(f"<i>🕐 {now_str}  ·  {source}  ·  {cmd_hint}</i>")

    return "\n".join(lines)


def _extract_items(raw: list[dict]) -> list[dict]:
    """Extract title + url from CryptoPanic result objects."""
    out = []
    for item in raw:
        title = _clean(item.get("title", "No title"))
        url   = item.get("url") or item.get("source", {}).get("url") or "#"
        out.append({"title": title, "url": url})
    return out


def _keyword_filter(items: list[dict], keywords: list[str], max_items: int) -> list[dict]:
    """Keep items whose title contains at least one keyword."""
    return [
        item for item in items
        if any(kw in item.get("title", "").lower() for kw in keywords)
    ][:max_items]


def _clean(text: str) -> str:
    """Unescape HTML entities and strip excess whitespace."""
    return html.unescape(text).strip()


def _now_label() -> str:
    """Return a human-readable 'just now' / 'N min ago' label."""
    return "Updated just now"


# ── Demo fallbacks ────────────────────────────────────────────────────────────

_DEMO_GENERAL: list[tuple[str, str]] = [
    ("Bitcoin ETF sees record $1.2B inflows in single day",         "https://cointelegraph.com"),
    ("Ethereum Layer-2 transactions hit all-time high",             "https://cointelegraph.com"),
    ("SEC reviews new spot crypto ETF applications",                "https://coindesk.com"),
    ("Solana DeFi TVL crosses $10 billion milestone",               "https://coindesk.com"),
    ("Federal Reserve signals pause; crypto markets rally",         "https://coindesk.com"),
]

_DEMO_COIN: dict[str, list[tuple[str, str]]] = {
    "BTC": [
        ("ETF approval speculation rises as BTC hits new highs",    "https://cointelegraph.com"),
        ("Bitcoin market sees slight correction after strong rally", "https://coindesk.com"),
        ("Whale accumulation signals long-term confidence in BTC",   "https://coindesk.com"),
        ("Miners increase hashrate ahead of next halving cycle",     "https://cointelegraph.com"),
        ("Institutional BTC holdings up 18% quarter-over-quarter",  "https://coindesk.com"),
    ],
    "ETH": [
        ("Ethereum L2 activity surges with record daily transactions","https://cointelegraph.com"),
        ("ETH staking yield rises as validator queue shrinks",       "https://coindesk.com"),
        ("Major DeFi protocol launches on Ethereum mainnet",         "https://cointelegraph.com"),
        ("EIP proposal aims to reduce ETH gas fees by 40%",         "https://coindesk.com"),
        ("Ethereum foundation report highlights ecosystem growth",   "https://cointelegraph.com"),
    ],
    "SOL": [
        ("Solana DEX volume outpaces Ethereum for third week",       "https://coindesk.com"),
        ("SOL mobile wallet integrations accelerate adoption",       "https://cointelegraph.com"),
        ("Solana validators upgrade to latest client version",       "https://coindesk.com"),
        ("New Solana memecoin season drives record fee revenue",     "https://cointelegraph.com"),
        ("SOL breaks key resistance; analysts target new highs",     "https://coindesk.com"),
    ],
    "XRP": [
        ("Ripple expands CBDC partnerships across Southeast Asia",   "https://cointelegraph.com"),
        ("XRP Ledger DEX volumes hit multi-month high",              "https://coindesk.com"),
        ("Ripple payment corridors now active in 50+ countries",     "https://cointelegraph.com"),
        ("Legal clarity lifts XRP trading volumes on US exchanges",  "https://coindesk.com"),
        ("XRP futures open interest reaches yearly peak",            "https://cointelegraph.com"),
    ],
}

_DEMO_GENERIC_COIN: list[tuple[str, str]] = [
    ("{name} network activity reaches 3-month high",               "https://coindesk.com"),
    ("{name} community votes on major protocol upgrade",           "https://cointelegraph.com"),
    ("Analysts split on {name} short-term price direction",        "https://coindesk.com"),
    ("{name} listed on two additional centralized exchanges",      "https://cointelegraph.com"),
    ("{name} developer activity up 24% month-over-month",         "https://coindesk.com"),
]


def _demo_general() -> str:
    items = [{"title": t, "url": u} for t, u in _DEMO_GENERAL]
    return _format_card(
        title="📰 Crypto News — Top Stories",
        items=items,
        source="Demo · set NEWS_API_KEY for live news",
        coin=None,
    )


def _demo_coin(symbol: str, meta: dict) -> str:
    raw = _DEMO_COIN.get(symbol)
    if raw:
        items = [{"title": t, "url": u} for t, u in raw]
    else:
        name  = meta.get("name", symbol)
        items = [
            {"title": t.replace("{name}", name), "url": u}
            for t, u in _DEMO_GENERIC_COIN
        ]

    return _format_card(
        title=f"📰 {meta['icon']} {meta['name']} News",
        items=items,
        source="Demo · set NEWS_API_KEY for live news",
        coin=symbol,
    )
