"""
services/digest_service.py — Daily digest content builder.

Compiles a morning briefing containing:
  1. Market overview — BTC + ETH price + 24h change
  2. Top 3 gainers and top 3 losers from Binance
  3. Fear & Greed-style BTC sentiment score
  4. Active alerts reminder

Fetches everything from Binance public API — no extra keys needed.
"""

import logging
from datetime import datetime, timezone

import aiohttp

from services.price_service import get_top_movers, COIN_META
from services.indicator_service import compute_indicators
from services.sentiment_service import compute_sentiment
from services.alert_store import get_user_alerts

logger = logging.getLogger(__name__)

BINANCE_TICKER  = "https://api.binance.com/api/v3/ticker/24hr"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


async def build_daily_digest(uid: int) -> str:
    """
    Build the full daily digest message for a user.
    Returns a formatted HTML string ready for bot.send_message().
    """
    now = datetime.now(timezone.utc)
    day = now.strftime("%A, %B %d %Y")

    lines = [
        f"🌅 <b>Good Morning! — Daily Crypto Digest</b>",
        f"<i>{day}  ·  UTC</i>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # ── Market overview: BTC + ETH ────────────────────────────────────────────
    overview = await _market_overview()
    lines += overview

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # ── Top movers ─────────────────────────────────────────────────────────────
    movers = await get_top_movers()
    gainers = movers.get("gainers", [])[:3]
    losers  = movers.get("losers",  [])[:3]

    if gainers:
        lines.append("🚀 <b>Top Gainers (24H)</b>")
        for c in gainers:
            lines.append(f"  🟢 <b>{c['symbol']}</b>  <code>${c['price']:,.4f}</code>  <b>+{c['change']:.2f}%</b>")

    if losers:
        lines.append("")
        lines.append("📉 <b>Top Losers (24H)</b>")
        for c in losers:
            lines.append(f"  🔴 <b>{c['symbol']}</b>  <code>${c['price']:,.4f}</code>  <b>{c['change']:.2f}%</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # ── BTC Sentiment ─────────────────────────────────────────────────────────
    try:
        btc_ind  = await compute_indicators("BTC")
        btc_sent = compute_sentiment(btc_ind)
        lines.append(
            f"🧠 <b>BTC Sentiment:</b>  {btc_sent.emoji} <b>{btc_sent.label}</b>  "
            f"<code>[{btc_sent.bar}]</code>  <b>{btc_sent.score}/100</b>"
        )
    except Exception:
        pass

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # ── Active alerts reminder ────────────────────────────────────────────────
    alerts = get_user_alerts(uid)
    if alerts:
        lines.append(f"🔔 <b>Your Active Alerts</b>  ({len(alerts)} set)")
        for a in alerts[:5]:
            lines.append(f"  {a.direction_emoji} <b>{a.symbol}</b> @ <code>${a.target:,.2f}</code>")
        if len(alerts) > 5:
            lines.append(f"  <i>…and {len(alerts) - 5} more</i>")
    else:
        lines.append("🔔 <b>No active alerts</b> — set one with /setalert BTC 70000")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        "<i>💡 /price · /signal · /analyze · /news\n"
        "⚠️ Not financial advice</i>"
    )

    return "\n".join(lines)


async def _market_overview() -> list[str]:
    """Fetch BTC and ETH ticker and return formatted lines."""
    lines = ["📊 <b>Market Overview</b>"]
    symbols = ["BTC", "ETH", "SOL"]

    try:
        quoted = ",".join(f'"{s}USDT"' for s in symbols)
        params = [("symbols", f"[{quoted}]")]
        async with aiohttp.ClientSession() as session:
            async with session.get(BINANCE_TICKER, params=params, timeout=REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                tickers = {t["symbol"]: t for t in await resp.json()}

        for sym in symbols:
            t = tickers.get(f"{sym}USDT")
            if not t:
                continue
            price  = float(t["lastPrice"])
            change = float(t["priceChangePercent"])
            dot    = "🟢" if change >= 0 else "🔴"
            meta   = COIN_META.get(sym, {"icon": "🪙", "name": sym})
            lines.append(
                f"  {dot} <b>{meta['icon']} {sym}</b>  "
                f"<code>${price:,.2f}</code>  "
                f"<i>({change:+.2f}%)</i>"
            )
    except Exception as exc:
        logger.warning("Market overview fetch failed: %s", exc)
        lines.append("  <i>Market data temporarily unavailable</i>")

    return lines
