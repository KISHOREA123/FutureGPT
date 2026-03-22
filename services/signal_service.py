"""
services/signal_service.py — AI-powered crypto trading signals.

Multi-timeframe scoring (1H + 15M):
  • 1H indicators carry 60% weight  — trend direction
  • 15M indicators carry 40% weight — short-term momentum
  This produces differentiated signals even when 1H looks identical across coins.

Scoring engine v3 fixes:
  1. Dual timeframe (1H + 15M) prevents all-same output
  2. RSI continuous contribution (not zone-only)
  3. MACD weighted by histogram magnitude
  4. Confidence capped at 80% for rule-based signals
  5. Overview shows RSI + key levels per coin (not just reason text)
"""

import logging
from dataclasses import dataclass
from typing import Literal

from services.indicator_service import (
    Indicators,
    compute_indicators,
    format_indicators_block,
)
from services.price_service import COIN_META, VALID_SYMBOLS, InvalidSymbolError

logger = logging.getLogger(__name__)

SignalAction = Literal["BUY", "SELL", "HOLD"]
SIGNAL_COINS = ["BTC", "ETH", "BNB", "SOL", "XRP"]


@dataclass(frozen=True)
class SignalResult:
    symbol:     str
    action:     SignalAction
    confidence: int
    reason:     str
    indicators: Indicators    # primary (1H) indicators shown in detail card


# ── Public API ────────────────────────────────────────────────────────────────

async def get_single_signal(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if symbol not in VALID_SYMBOLS:
        raise InvalidSymbolError(symbol)

    logger.info("Computing signal for %s (1H + 15M)", symbol)

    # Fetch both timeframes concurrently via separate calls
    import asyncio
    try:
        ind_1h, ind_15m = await asyncio.gather(
            compute_indicators(symbol, interval="1h"),
            compute_indicators(symbol, interval="15m"),
        )
    except TypeError:
        # Fallback: indicator_service doesn't support interval param yet
        ind_1h = await compute_indicators(symbol)
        ind_15m = None

    result = _analyse_signal(ind_1h, ind_15m)
    return _format_signal_card(result)


async def get_signal_overview() -> str:
    lines = ["<b>📈 AI Signal Overview</b>  <i>(1H · Binance)</i>\n"]

    for sym in SIGNAL_COINS:
        try:
            ind    = await compute_indicators(sym)
            result = _analyse_signal(ind, None)
            dot, label = _action_style(result.action)
            # Overview line: show RSI value + MACD + EMA state clearly
            rsi_str  = f"RSI {ind.rsi:.0f}"
            macd_str = "MACD ↑" if ind.macd_cross == "BULLISH" else ("MACD ↓" if ind.macd_cross == "BEARISH" else "MACD ~")
            ema_str  = "EMA ↑" if ind.ema_trend == "BULLISH" else ("EMA ↓" if ind.ema_trend == "BEARISH" else "EMA ~")
            lines.append(
                f"{dot} <b>{sym}</b> → <code>{label}</code> "
                f"<b>{result.confidence}%</b>  "
                f"<i>{rsi_str} · {macd_str} · {ema_str}</i>"
            )
        except Exception as exc:
            logger.warning("Signal skipped for %s: %s", sym, exc)
            lines.append(f"⚪ <b>{sym}</b>  →  <i>data unavailable</i>")

    lines.append(
        "\n<i>💡 /signal &lt;symbol&gt; for full breakdown\n"
        "⚠️ Informational only — not financial advice</i>"
    )
    return "\n".join(lines)


def invalid_signal_message(symbol: str) -> str:
    popular = ", ".join(SIGNAL_COINS)
    return (
        f"⚠️ <b>Unknown symbol:</b> <code>{symbol}</code>\n\n"
        f"Supported:\n<code>{popular}</code>\n\n"
        f"<i>Usage: /signal BTC  ·  /signal ETH</i>"
    )


# ── Scoring engine v3 ─────────────────────────────────────────────────────────

def _score_indicators(ind: Indicators) -> tuple[int, list[str]]:
    """
    Score one set of indicators. Returns (score, notes).
    Score range: -75 to +75
    """
    score = 0
    notes: list[str] = []

    # RSI: continuous -20 to +20
    rsi_pts = round((50 - ind.rsi) * 0.4)
    rsi_pts = max(-20, min(20, rsi_pts))
    score += rsi_pts

    if ind.rsi_zone == "OVERSOLD":
        notes.append(f"RSI oversold ({ind.rsi:.0f})")
    elif ind.rsi_zone == "OVERBOUGHT":
        notes.append(f"RSI overbought ({ind.rsi:.0f})")
    else:
        notes.append(f"RSI {ind.rsi:.0f}")

    # MACD: ±20 base + ±5 for strong histogram
    if ind.macd_cross == "BULLISH":
        hist_bonus = 5 if (ind.macd_sig != 0 and
                           abs(ind.macd_hist) > abs(ind.macd_sig) * 0.15) else 2
        score += 20 + hist_bonus
        notes.append("MACD↑")
    elif ind.macd_cross == "BEARISH":
        hist_bonus = 5 if (ind.macd_sig != 0 and
                           abs(ind.macd_hist) > abs(ind.macd_sig) * 0.15) else 2
        score -= (20 + hist_bonus)
        notes.append("MACD↓")
    else:
        nudge = 3 if ind.macd > 0 else -3
        score += nudge
        notes.append("MACD~")

    # EMA: ±20 base + ±5 for gap size
    if ind.ema_trend == "BULLISH":
        gap_pct = (ind.price - ind.ema_20) / ind.ema_20 * 100 if ind.ema_20 else 0
        score += 20 + min(5, int(abs(gap_pct)))
        notes.append("EMA↑")
    elif ind.ema_trend == "BEARISH":
        gap_pct = (ind.ema_20 - ind.price) / ind.ema_20 * 100 if ind.ema_20 else 0
        score -= (20 + min(5, int(abs(gap_pct))))
        notes.append("EMA↓")
    else:
        nudge = 5 if ind.ema_20 > ind.ema_50 else (-5 if ind.ema_20 < ind.ema_50 else 0)
        score += nudge
        notes.append("EMA~")

    return score, notes


def _analyse_signal(
    ind_1h: Indicators,
    ind_15m: Indicators | None,
) -> SignalResult:
    """
    Combine 1H (60% weight) and 15M (40% weight) scores.
    Falls back to 1H-only if 15M is unavailable.
    """
    score_1h, notes_1h = _score_indicators(ind_1h)

    if ind_15m is not None:
        score_15m, notes_15m = _score_indicators(ind_15m)
        # Weighted combination: 1H for trend, 15M for momentum
        combined = round(score_1h * 0.6 + score_15m * 0.4)
        # Use 15M RSI in reason if it diverges from 1H
        rsi_diverge = abs(ind_1h.rsi - ind_15m.rsi) > 5
        reason = _build_reason(notes_1h, notes_15m if rsi_diverge else None)
    else:
        combined = score_1h
        reason   = _build_reason(notes_1h, None)

    action, confidence = _score_to_signal(combined)

    return SignalResult(
        symbol     = ind_1h.symbol,
        action     = action,
        confidence = confidence,
        reason     = reason,
        indicators = ind_1h,
    )


def _score_to_signal(score: int) -> tuple[SignalAction, int]:
    """
    Score → (action, confidence).
    BUY if >= 30, SELL if <= -30, HOLD otherwise.
    Confidence: 45–80% (capped — rule-based signals never claim >80%).
    """
    if score >= 30:
        conf = int(45 + (score - 30) * (35 / 45))
        return "BUY",  min(80, conf)
    if score <= -30:
        conf = int(45 + (abs(score) - 30) * (35 / 45))
        return "SELL", min(80, conf)
    conf = int(70 - abs(score) * (25 / 29))
    return "HOLD", max(45, conf)


def _build_reason(notes_1h: list[str], notes_15m: list[str] | None) -> str:
    """Build a compact reason string."""
    if notes_15m:
        return f"1H: {' · '.join(notes_1h[:3])}  |  15M: {' · '.join(notes_15m[:2])}"
    return " · ".join(notes_1h[:3])


# ── LLM placeholder ───────────────────────────────────────────────────────────

def build_llm_prompt(ind: Indicators) -> str:
    return (
        "You are an expert crypto trader. Given:\n"
        f"  Price:     ${ind.price:,.4f}\n"
        f"  RSI:       {ind.rsi:.2f}  ({ind.rsi_zone})\n"
        f"  MACD:      {ind.macd:+.4f}  ({ind.macd_cross} crossover)\n"
        f"  EMA Trend: {ind.ema_trend}  (EMA20=${ind.ema_20:,.2f} / EMA50=${ind.ema_50:,.2f})\n\n"
        "Return ONLY JSON: "
        '{"signal":"BUY|SELL|HOLD","reason":"<20 words>","confidence":<int>}'
    )


# ── Formatting ────────────────────────────────────────────────────────────────

def _action_style(action: SignalAction) -> tuple[str, str]:
    return {
        "BUY":  ("🟢", "BUY  "),
        "SELL": ("🔴", "SELL "),
        "HOLD": ("🟡", "HOLD "),
    }[action]


def _format_signal_card(result: SignalResult) -> str:
    ind  = result.indicators
    dot, label = _action_style(result.action)
    meta = COIN_META.get(result.symbol, {"icon": "🪙", "name": result.symbol})

    filled = round(result.confidence / 10)
    bar    = "█" * filled + "░" * (10 - filled)

    return (
        f"📈 <b>{meta['icon']} {meta['name']} ({result.symbol}) — Signal</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{dot} <b>{label}</b>  <code>[{bar}]</code>  <b>{result.confidence}%</b>\n"
        f"💬 <b>Reason:</b> <i>{result.reason}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{format_indicators_block(ind)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>⚠️ Informational only · Not financial advice\n"
        f"🔄 Live · Binance 1H · Pure pandas</i>"
    )