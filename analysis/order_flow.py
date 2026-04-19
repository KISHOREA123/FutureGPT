"""
Order Flow / Whale Activity Analyzer
Detects institutional activity through volume anomalies:
  - Volume Climax (massive volume + large body)
  - Absorption (high volume + small body = contested zone)
  - Exhaustion (volume spike + opposing wicks)
  - Accumulation / Distribution (OBV divergence)
  - Large Player Candles (outsized body + volume)

Produces a composite "Whale Score" (0-100).
"""
import numpy as np
import pandas as pd
from config import (
    WHALE_VOLUME_CLIMAX_THRESHOLD,
    WHALE_ABSORPTION_THRESHOLD,
    WHALE_EXHAUSTION_THRESHOLD,
)


def _detect_volume_climax(df: pd.DataFrame, lookback: int = 50) -> list:
    """Detect volume climax events (extreme volume + large body)."""
    events = []
    if len(df) < lookback:
        return events

    avg_vol = df["volume"].iloc[-lookback:].mean()
    avg_body = (df["close"] - df["open"]).abs().iloc[-lookback:].mean()

    for i in range(-min(10, len(df)), 0):
        candle = df.iloc[i]
        vol = candle["volume"]
        body = abs(candle["close"] - candle["open"])

        if vol > avg_vol * WHALE_VOLUME_CLIMAX_THRESHOLD and body > avg_body * 1.5:
            direction = "bullish" if candle["close"] > candle["open"] else "bearish"
            events.append({
                "type": "volume_climax",
                "direction": direction,
                "volume_ratio": round(vol / avg_vol, 1),
                "index": len(df) + i,
                "label": f"🐋 Volume Climax ({direction.upper()}) — {vol/avg_vol:.1f}x avg volume",
            })
    return events


def _detect_absorption(df: pd.DataFrame, lookback: int = 50) -> list:
    """Detect absorption (high volume but small body = contested zone)."""
    events = []
    if len(df) < lookback:
        return events

    avg_vol = df["volume"].iloc[-lookback:].mean()
    avg_body = (df["close"] - df["open"]).abs().iloc[-lookback:].mean()

    for i in range(-min(10, len(df)), 0):
        candle = df.iloc[i]
        vol = candle["volume"]
        body = abs(candle["close"] - candle["open"])
        full_range = candle["high"] - candle["low"]

        if (vol > avg_vol * WHALE_ABSORPTION_THRESHOLD and
                body < avg_body * 0.5 and full_range > 0):
            wick_ratio = body / full_range
            events.append({
                "type": "absorption",
                "volume_ratio": round(vol / avg_vol, 1),
                "wick_dominance": round(1 - wick_ratio, 2),
                "index": len(df) + i,
                "label": f"🧱 Absorption — {vol/avg_vol:.1f}x vol, small body (contested zone)",
            })
    return events


def _detect_exhaustion(df: pd.DataFrame, lookback: int = 50) -> list:
    """Detect exhaustion (volume spike + opposing wick signals reversal)."""
    events = []
    if len(df) < lookback:
        return events

    avg_vol = df["volume"].iloc[-lookback:].mean()

    for i in range(-min(10, len(df)), 0):
        candle = df.iloc[i]
        vol = candle["volume"]
        body = abs(candle["close"] - candle["open"])
        full_range = candle["high"] - candle["low"]
        upper_w = candle["high"] - max(candle["open"], candle["close"])
        lower_w = min(candle["open"], candle["close"]) - candle["low"]

        if vol < avg_vol * WHALE_EXHAUSTION_THRESHOLD:
            continue

        # Bullish exhaustion: bearish candle with long lower wick
        if (candle["close"] < candle["open"] and
                lower_w > body * 2 and full_range > 0):
            events.append({
                "type": "exhaustion",
                "direction": "bullish_reversal",
                "volume_ratio": round(vol / avg_vol, 1),
                "index": len(df) + i,
                "label": "⚡ Selling Exhaustion — Potential bullish reversal",
            })

        # Bearish exhaustion: bullish candle with long upper wick
        if (candle["close"] > candle["open"] and
                upper_w > body * 2 and full_range > 0):
            events.append({
                "type": "exhaustion",
                "direction": "bearish_reversal",
                "volume_ratio": round(vol / avg_vol, 1),
                "index": len(df) + i,
                "label": "⚡ Buying Exhaustion — Potential bearish reversal",
            })

    return events


def _detect_accumulation_distribution(df: pd.DataFrame, lookback: int = 50) -> dict:
    """Detect accumulation/distribution phase via OBV divergence."""
    if len(df) < lookback:
        return {"phase": "unknown", "label": "N/A"}

    close = df["close"].iloc[-lookback:]
    volume = df["volume"].iloc[-lookback:]

    # Simple OBV
    obv = pd.Series(0.0, index=close.index)
    for j in range(1, len(close)):
        if close.iloc[j] > close.iloc[j - 1]:
            obv.iloc[j] = obv.iloc[j - 1] + volume.iloc[j]
        elif close.iloc[j] < close.iloc[j - 1]:
            obv.iloc[j] = obv.iloc[j - 1] - volume.iloc[j]
        else:
            obv.iloc[j] = obv.iloc[j - 1]

    # Compare price trend vs OBV trend
    price_change = close.iloc[-1] - close.iloc[0]
    obv_change = obv.iloc[-1] - obv.iloc[0]

    if price_change < 0 and obv_change > 0:
        return {
            "phase": "accumulation",
            "label": "📦 Accumulation Phase — Smart money buying while price falls",
        }
    elif price_change > 0 and obv_change < 0:
        return {
            "phase": "distribution",
            "label": "📤 Distribution Phase — Smart money selling while price rises",
        }
    elif price_change > 0 and obv_change > 0:
        return {"phase": "markup", "label": "📈 Markup Phase — Healthy uptrend with volume"}
    else:
        return {"phase": "markdown", "label": "📉 Markdown Phase — Confirmed downtrend"}


def _detect_large_player_candles(df: pd.DataFrame, lookback: int = 50) -> list:
    """Detect candles with outsized body + volume (institutional moves)."""
    events = []
    if len(df) < lookback:
        return events

    avg_body = (df["close"] - df["open"]).abs().iloc[-lookback:].mean()
    avg_vol = df["volume"].iloc[-lookback:].mean()

    for i in range(-min(5, len(df)), 0):
        candle = df.iloc[i]
        body = abs(candle["close"] - candle["open"])
        vol = candle["volume"]

        if body > avg_body * 2 and vol > avg_vol * 1.5:
            direction = "bullish" if candle["close"] > candle["open"] else "bearish"
            events.append({
                "type": "large_player",
                "direction": direction,
                "body_ratio": round(body / avg_body, 1),
                "volume_ratio": round(vol / avg_vol, 1),
                "index": len(df) + i,
                "label": f"🏦 Large Player Candle ({direction.upper()}) — {body/avg_body:.1f}x body, {vol/avg_vol:.1f}x vol",
            })
    return events


def _calculate_whale_score(
    climax_events: list,
    absorption_events: list,
    exhaustion_events: list,
    accum_dist: dict,
    large_candles: list,
) -> int:
    """Compute composite whale activity score (0-100)."""
    score = 0

    # Climax events (max 30 pts)
    score += min(len(climax_events) * 15, 30)

    # Absorption events (max 20 pts)
    score += min(len(absorption_events) * 10, 20)

    # Exhaustion events (max 15 pts)
    score += min(len(exhaustion_events) * 10, 15)

    # Accumulation/Distribution phase (max 15 pts)
    phase = accum_dist.get("phase", "unknown")
    if phase in ("accumulation", "distribution"):
        score += 15
    elif phase in ("markup", "markdown"):
        score += 5

    # Large player candles (max 20 pts)
    score += min(len(large_candles) * 10, 20)

    return min(score, 100)


def analyze_order_flow(df: pd.DataFrame) -> dict:
    """
    Full order flow analysis — detects whale activity patterns.

    Returns:
        dict with all detected events and composite whale score
    """
    if len(df) < 30:
        return {
            "whale_score": 0,
            "whale_label": "Insufficient Data",
            "events": [],
            "accum_dist": {"phase": "unknown", "label": "N/A"},
            "bias": "neutral",
        }

    climax = _detect_volume_climax(df)
    absorption = _detect_absorption(df)
    exhaustion = _detect_exhaustion(df)
    accum_dist = _detect_accumulation_distribution(df)
    large_candles = _detect_large_player_candles(df)

    whale_score = _calculate_whale_score(
        climax, absorption, exhaustion, accum_dist, large_candles
    )

    # Whale activity label
    if whale_score >= 70:
        whale_label = "🐋 HIGH — Significant institutional activity"
    elif whale_score >= 40:
        whale_label = "🐳 MODERATE — Some whale footprints detected"
    elif whale_score >= 15:
        whale_label = "🐟 LOW — Minor institutional signals"
    else:
        whale_label = "🦐 NONE — Retail-dominated price action"

    # All events combined
    all_events = climax + absorption + exhaustion + large_candles

    # Determine bias from events
    bullish_events = sum(
        1 for e in all_events
        if e.get("direction") in ("bullish", "bullish_reversal")
    )
    bearish_events = sum(
        1 for e in all_events
        if e.get("direction") in ("bearish", "bearish_reversal")
    )

    if bullish_events > bearish_events:
        bias = "bullish"
    elif bearish_events > bullish_events:
        bias = "bearish"
    else:
        bias = "neutral"

    return {
        "whale_score": whale_score,
        "whale_label": whale_label,
        "events": all_events[:10],  # Top 10 recent events
        "climax_count": len(climax),
        "absorption_count": len(absorption),
        "exhaustion_count": len(exhaustion),
        "large_player_count": len(large_candles),
        "accum_dist": accum_dist,
        "bias": bias,
        "bullish_events": bullish_events,
        "bearish_events": bearish_events,
    }
