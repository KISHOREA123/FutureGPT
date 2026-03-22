"""
services/pattern_service.py — Chart pattern recognition using OHLCV data.

Detects 8 classic patterns from the last 50 candles:
  1. Double Top        — bearish reversal
  2. Double Bottom     — bullish reversal
  3. Higher Highs / Higher Lows (Uptrend)
  4. Lower Highs / Lower Lows  (Downtrend)
  5. Ascending Triangle  — bullish breakout
  6. Descending Triangle — bearish breakdown
  7. Consolidation / Range — neutral
  8. Bull Flag / Bear Flag  — continuation

All pure pandas math on the OHLCV DataFrame — no third-party TA library.
Returns formatted HTML for embedding in the analyze card.
"""

import logging
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

PATTERN_CANDLES = 50   # candles analysed (last 50 of the 100 fetched)


@dataclass
class PatternResult:
    name:        str       # e.g. "Double Bottom"
    signal:      str       # "BULLISH" / "BEARISH" / "NEUTRAL"
    confidence:  int       # 0-100
    description: str       # one-sentence plain English explanation
    emoji:       str       # visual indicator


def detect_patterns(df: pd.DataFrame) -> list[PatternResult]:
    """
    Analyse OHLCV DataFrame and return a list of detected patterns.
    Takes the last PATTERN_CANDLES rows for analysis.
    Returns an empty list if data is insufficient.
    """
    if len(df) < 20:
        return []

    data = df.tail(PATTERN_CANDLES).copy()
    patterns: list[PatternResult] = []

    # Run each detector; append result if confidence > 0
    for detector in [
        _detect_double_top,
        _detect_double_bottom,
        _detect_trend_structure,
        _detect_triangle,
        _detect_flag,
        _detect_consolidation,
    ]:
        result = detector(data)
        if result and result.confidence >= 40:
            patterns.append(result)

    # Return top 3 by confidence (avoid noise)
    patterns.sort(key=lambda p: p.confidence, reverse=True)
    return patterns[:3]


def format_patterns_card(patterns: list[PatternResult]) -> str:
    """Format detected patterns into a Telegram HTML card section."""
    if not patterns:
        return (
            "📐 <b>Chart Patterns</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>No strong patterns detected on 1H chart</i>"
        )

    lines = [
        "📐 <b>Chart Patterns</b>  <i>(1H · Last 50 candles)</i>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for p in patterns:
        dot = "🟢" if p.signal == "BULLISH" else ("🔴" if p.signal == "BEARISH" else "🟡")
        lines.append(
            f"{p.emoji} <b>{p.name}</b>  {dot} <i>{p.signal}</i>  "
            f"<code>{p.confidence}%</code>\n"
            f"   <i>{p.description}</i>"
        )
    return "\n".join(lines)


# ── Pattern detectors ─────────────────────────────────────────────────────────

def _detect_double_top(df: pd.DataFrame) -> PatternResult | None:
    """
    Double Top: two peaks of similar height with a valley between them.
    Bearish reversal signal.
    """
    highs  = df["high"].values
    n      = len(highs)
    window = max(5, n // 5)

    # Find local maxima
    peaks = []
    for i in range(window, n - window):
        if highs[i] == max(highs[i - window:i + window + 1]):
            peaks.append((i, highs[i]))

    if len(peaks) < 2:
        return None

    # Check last two peaks
    p1_idx, p1_val = peaks[-2]
    p2_idx, p2_val = peaks[-1]

    if p2_idx <= p1_idx:
        return None

    # Peaks must be within 3% of each other
    similarity = 1 - abs(p1_val - p2_val) / max(p1_val, p2_val)
    if similarity < 0.97:
        return None

    # Valley between peaks must be meaningfully lower (>2%)
    valley = min(df["low"].values[p1_idx:p2_idx + 1])
    depth  = (min(p1_val, p2_val) - valley) / min(p1_val, p2_val)
    if depth < 0.02:
        return None

    confidence = min(90, int(similarity * 70 + depth * 200))
    return PatternResult(
        name        = "Double Top",
        signal      = "BEARISH",
        confidence  = confidence,
        description = f"Two peaks near ${p1_val:,.2f} signal resistance — bearish reversal likely",
        emoji       = "🔻",
    )


def _detect_double_bottom(df: pd.DataFrame) -> PatternResult | None:
    """
    Double Bottom: two troughs of similar depth with a peak between them.
    Bullish reversal signal.
    """
    lows   = df["low"].values
    n      = len(lows)
    window = max(5, n // 5)

    troughs = []
    for i in range(window, n - window):
        if lows[i] == min(lows[i - window:i + window + 1]):
            troughs.append((i, lows[i]))

    if len(troughs) < 2:
        return None

    t1_idx, t1_val = troughs[-2]
    t2_idx, t2_val = troughs[-1]

    if t2_idx <= t1_idx:
        return None

    similarity = 1 - abs(t1_val - t2_val) / max(t1_val, t2_val)
    if similarity < 0.97:
        return None

    peak   = max(df["high"].values[t1_idx:t2_idx + 1])
    height = (peak - max(t1_val, t2_val)) / max(t1_val, t2_val)
    if height < 0.02:
        return None

    confidence = min(90, int(similarity * 70 + height * 200))
    return PatternResult(
        name        = "Double Bottom",
        signal      = "BULLISH",
        confidence  = confidence,
        description = f"Two lows near ${t1_val:,.2f} signal strong support — bullish reversal likely",
        emoji       = "🔺",
    )


def _detect_trend_structure(df: pd.DataFrame) -> PatternResult | None:
    """
    Detect uptrend (HH+HL) or downtrend (LH+LL) via swing structure.
    """
    closes = df["close"].values
    n      = len(closes)
    thirds = n // 3

    early  = closes[:thirds]
    late   = closes[2 * thirds:]

    early_high = np.max(early)
    early_low  = np.min(early)
    late_high  = np.max(late)
    late_low   = np.min(late)
    late_close = closes[-1]
    early_close = np.mean(early)

    change_pct = (late_close - early_close) / early_close * 100

    if late_high > early_high and late_low > early_low and change_pct > 2:
        conf = min(85, int(40 + abs(change_pct) * 3))
        return PatternResult(
            name        = "Uptrend (HH/HL)",
            signal      = "BULLISH",
            confidence  = conf,
            description = f"Higher highs and higher lows — sustained uptrend (+{change_pct:.1f}%)",
            emoji       = "📈",
        )

    if late_high < early_high and late_low < early_low and change_pct < -2:
        conf = min(85, int(40 + abs(change_pct) * 3))
        return PatternResult(
            name        = "Downtrend (LH/LL)",
            signal      = "BEARISH",
            confidence  = conf,
            description = f"Lower highs and lower lows — sustained downtrend ({change_pct:.1f}%)",
            emoji       = "📉",
        )

    return None


def _detect_triangle(df: pd.DataFrame) -> PatternResult | None:
    """
    Detect ascending triangle (bullish) or descending triangle (bearish).
    Ascending: highs flat, lows rising.
    Descending: lows flat, highs falling.
    """
    highs = df["high"].values
    lows  = df["low"].values
    n     = len(highs)

    # Fit linear regression to highs and lows
    x = np.arange(n)

    high_slope = float(np.polyfit(x, highs, 1)[0])
    low_slope  = float(np.polyfit(x, lows,  1)[0])

    price_range = float(np.mean(highs)) - float(np.mean(lows))
    if price_range == 0:
        return None

    # Normalise slopes relative to price level
    norm_high = high_slope / price_range * n
    norm_low  = low_slope  / price_range * n

    # Ascending: highs flat (|slope| < 0.05), lows rising (slope > 0.05)
    if abs(norm_high) < 0.05 and norm_low > 0.05:
        conf = min(80, int(50 + norm_low * 100))
        return PatternResult(
            name        = "Ascending Triangle",
            signal      = "BULLISH",
            confidence  = conf,
            description = "Flat resistance + rising lows — bullish breakout setup",
            emoji       = "△",
        )

    # Descending: lows flat, highs falling
    if abs(norm_low) < 0.05 and norm_high < -0.05:
        conf = min(80, int(50 + abs(norm_high) * 100))
        return PatternResult(
            name        = "Descending Triangle",
            signal      = "BEARISH",
            confidence  = conf,
            description = "Flat support + falling highs — bearish breakdown setup",
            emoji       = "▽",
        )

    return None


def _detect_flag(df: pd.DataFrame) -> PatternResult | None:
    """
    Detect Bull Flag (strong up move + consolidation) or Bear Flag.
    """
    closes = df["close"].values
    n      = len(closes)
    pole   = n // 3     # "pole" is first third, "flag" is last two-thirds

    pole_move  = (closes[pole] - closes[0]) / closes[0] * 100
    flag_range = (max(closes[pole:]) - min(closes[pole:])) / closes[pole] * 100

    # Bull flag: pole up >4%, flag consolidates <3%
    if pole_move > 4 and flag_range < 3:
        conf = min(80, int(50 + pole_move * 3))
        return PatternResult(
            name        = "Bull Flag",
            signal      = "BULLISH",
            confidence  = conf,
            description = f"Sharp +{pole_move:.1f}% move followed by tight consolidation — continuation likely",
            emoji       = "🚩",
        )

    # Bear flag: pole down <-4%, consolidates <3%
    if pole_move < -4 and flag_range < 3:
        conf = min(80, int(50 + abs(pole_move) * 3))
        return PatternResult(
            name        = "Bear Flag",
            signal      = "BEARISH",
            confidence  = conf,
            description = f"Sharp {pole_move:.1f}% drop followed by tight consolidation — breakdown likely",
            emoji       = "🏴",
        )

    return None


def _detect_consolidation(df: pd.DataFrame) -> PatternResult | None:
    """
    Detect price consolidation / ranging — low volatility, no trend.
    """
    closes = df["close"].values
    mean   = np.mean(closes)
    std    = np.std(closes)

    if mean == 0:
        return None

    cv = std / mean   # coefficient of variation
    # Low CV = tight range = consolidation
    if cv < 0.015:
        conf = min(80, int((0.015 - cv) / 0.015 * 80))
        return PatternResult(
            name        = "Consolidation",
            signal      = "NEUTRAL",
            confidence  = conf,
            description = f"Tight range (±{cv*100:.1f}%) — wait for breakout direction",
            emoji       = "↔️",
        )

    return None
