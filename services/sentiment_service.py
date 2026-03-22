"""
services/sentiment_service.py — Market Sentiment Score per coin.

Combines 5 signals into a 0-100 score with a clear label:
  1. RSI position        (0-25 pts)  — momentum / exhaustion
  2. MACD cross          (0-20 pts)  — trend change
  3. EMA trend           (0-20 pts)  — macro direction
  4. Price vs EMA20      (0-15 pts)  — short-term strength
  5. Volume momentum     (0-20 pts)  — conviction behind move

Score → Label:
  80-100  🔥 Extreme Greed
  60-79   😄 Greed
  45-59   😐 Neutral
  25-44   😟 Fear
  0-24    😱 Extreme Fear
"""

import logging
from dataclasses import dataclass
from services.indicator_service import Indicators

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SentimentResult:
    score:       int        # 0-100
    label:       str        # "Extreme Greed" etc.
    emoji:       str        # 🔥 😄 😐 😟 😱
    color_dot:   str        # 🟢 🟡 🔴
    breakdown:   dict       # component scores for transparency
    bar:         str        # visual bar e.g. ████████░░


def compute_sentiment(ind: Indicators) -> SentimentResult:
    """
    Compute market sentiment for a coin from its Indicators.
    Returns a SentimentResult with score, label, and visual elements.
    """
    breakdown = {}

    # ── 1. RSI Component (0-25 pts) ───────────────────────────────────────────
    # RSI 20 → 25pts (strongly oversold = fear, potential reversal)
    # RSI 50 → 12pts (neutral)
    # RSI 80 → 0pts  (overbought = greed)
    # Note: HIGH RSI = HIGH sentiment (market is greedy)
    rsi_norm       = (ind.rsi - 20) / 60   # normalise 20-80 → 0-1
    rsi_norm       = max(0.0, min(1.0, rsi_norm))
    rsi_pts        = round(rsi_norm * 25)
    breakdown["RSI"] = rsi_pts

    # ── 2. MACD Cross Component (0-20 pts) ────────────────────────────────────
    if ind.macd_cross == "BULLISH":
        macd_pts = 20
    elif ind.macd_cross == "BEARISH":
        macd_pts = 0
    else:
        # Flat: score based on whether MACD is above or below zero
        macd_pts = 12 if ind.macd > 0 else 8
    breakdown["MACD"] = macd_pts

    # ── 3. EMA Trend Component (0-20 pts) ─────────────────────────────────────
    if ind.ema_trend == "BULLISH":
        ema_pts = 20
    elif ind.ema_trend == "BEARISH":
        ema_pts = 0
    else:
        ema_pts = 10
    breakdown["EMA"] = ema_pts

    # ── 4. Price vs EMA20 (0-15 pts) ──────────────────────────────────────────
    # How far price is above/below its short-term average
    if ind.ema_20 > 0:
        pct_above = (ind.price - ind.ema_20) / ind.ema_20 * 100
        # +5% above EMA20 → 15pts, -5% below → 0pts, 0% → 7pts
        pct_norm  = (pct_above + 5) / 10    # -5% → 0, +5% → 1
        pct_norm  = max(0.0, min(1.0, pct_norm))
        price_pts = round(pct_norm * 15)
    else:
        price_pts = 7
    breakdown["Price/EMA"] = price_pts

    # ── 5. MACD Histogram Momentum (0-20 pts) ─────────────────────────────────
    # Histogram magnitude shows conviction: large positive = strong bullish momentum
    if ind.macd_sig != 0:
        hist_ratio = ind.macd_hist / abs(ind.macd_sig)
        # Clamp to [-1, +1] then normalize to [0, 20]
        hist_ratio = max(-1.0, min(1.0, hist_ratio))
        momentum_pts = round((hist_ratio + 1) / 2 * 20)
    else:
        momentum_pts = 10
    breakdown["Momentum"] = momentum_pts

    # ── Total ─────────────────────────────────────────────────────────────────
    score = sum(breakdown.values())
    score = max(0, min(100, score))

    label, emoji, color_dot = _score_to_label(score)
    bar = _make_bar(score)

    return SentimentResult(
        score     = score,
        label     = label,
        emoji     = emoji,
        color_dot = color_dot,
        breakdown = breakdown,
        bar       = bar,
    )


def format_sentiment_card(sent: SentimentResult, symbol: str) -> str:
    """Render a compact sentiment card for embedding in the analyze card."""
    breakdown_str = "  ".join(
        f"{k}:<b>{v}</b>" for k, v in sent.breakdown.items()
    )
    return (
        f"🧠 <b>Market Sentiment</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{sent.color_dot} <b>{sent.label}</b>  {sent.emoji}  "
        f"<code>[{sent.bar}]</code>  <b>{sent.score}/100</b>\n"
        f"<i>{breakdown_str}</i>"
    )


def _score_to_label(score: int) -> tuple[str, str, str]:
    """Return (label, emoji, color_dot) for a score."""
    if score >= 80:
        return "Extreme Greed", "🔥", "🟢"
    if score >= 60:
        return "Greed",         "😄", "🟢"
    if score >= 45:
        return "Neutral",       "😐", "🟡"
    if score >= 25:
        return "Fear",          "😟", "🔴"
    return     "Extreme Fear",  "😱", "🔴"


def _make_bar(score: int, length: int = 10) -> str:
    """Visual progress bar: ████████░░"""
    filled = round(score / 100 * length)
    return "█" * filled + "░" * (length - filled)
