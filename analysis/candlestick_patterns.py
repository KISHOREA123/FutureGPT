"""
Candlestick Pattern Detector — Enhanced v2.0
Detects 19 candlestick patterns (single, double, and triple candle patterns).
"""
import pandas as pd
import numpy as np


def body_size(candle: pd.Series) -> float:
    return abs(candle["close"] - candle["open"])

def full_range(candle: pd.Series) -> float:
    return candle["high"] - candle["low"]

def upper_wick(candle: pd.Series) -> float:
    return candle["high"] - max(candle["open"], candle["close"])

def lower_wick(candle: pd.Series) -> float:
    return min(candle["open"], candle["close"]) - candle["low"]

def is_bullish(candle: pd.Series) -> bool:
    return candle["close"] > candle["open"]

def is_bearish(candle: pd.Series) -> bool:
    return candle["close"] < candle["open"]

def body_mid(candle: pd.Series) -> float:
    return (candle["open"] + candle["close"]) / 2


def detect_patterns(df: pd.DataFrame) -> list:
    """Scan last candles for 19 known candlestick patterns."""
    patterns = []
    n = len(df)
    if n < 5:
        return patterns

    c0 = df.iloc[-1]   # Latest candle
    c1 = df.iloc[-2]   # Previous candle
    c2 = df.iloc[-3]   # Two candles ago
    c3 = df.iloc[-4] if n >= 4 else None
    c4 = df.iloc[-5] if n >= 5 else None

    avg_body = df["close"].iloc[-20:].sub(df["open"].iloc[-20:]).abs().mean()
    avg_range = (df["high"] - df["low"]).iloc[-20:].mean()

    # ═══════════════════════════════════════════════════════
    # SINGLE CANDLE PATTERNS
    # ═══════════════════════════════════════════════════════

    # Doji — Indecision
    if full_range(c0) > 0 and body_size(c0) <= 0.1 * full_range(c0):
        # Classify Doji sub-type
        uw = upper_wick(c0)
        lw = lower_wick(c0)
        if uw > 2 * body_size(c0) and lw > 2 * body_size(c0):
            patterns.append({"pattern": "Long-Legged Doji ✝️", "type": "neutral", "candle": "Latest", "reliability": "moderate"})
        elif uw > 2 * body_size(c0) and lw < body_size(c0):
            patterns.append({"pattern": "Gravestone Doji 🪦", "type": "bearish", "candle": "Latest", "reliability": "moderate"})
        elif lw > 2 * body_size(c0) and uw < body_size(c0):
            patterns.append({"pattern": "Dragonfly Doji 🐉", "type": "bullish", "candle": "Latest", "reliability": "moderate"})
        else:
            patterns.append({"pattern": "Doji ⚪", "type": "neutral", "candle": "Latest", "reliability": "low"})

    # Hammer (bullish reversal at bottom)
    if (body_size(c0) > 0 and
            lower_wick(c0) >= 2 * body_size(c0) and
            upper_wick(c0) <= 0.3 * body_size(c0) and
            is_bullish(c0)):
        patterns.append({"pattern": "Hammer 🔨", "type": "bullish", "candle": "Latest", "reliability": "high"})

    # Shooting Star (bearish reversal at top)
    if (body_size(c0) > 0 and
            upper_wick(c0) >= 2 * body_size(c0) and
            lower_wick(c0) <= 0.3 * body_size(c0) and
            is_bearish(c0)):
        patterns.append({"pattern": "Shooting Star 💫", "type": "bearish", "candle": "Latest", "reliability": "high"})

    # Inverted Hammer
    if (body_size(c0) > 0 and
            upper_wick(c0) >= 2 * body_size(c0) and
            lower_wick(c0) <= 0.3 * body_size(c0) and
            is_bullish(c0)):
        patterns.append({"pattern": "Inverted Hammer 🔼", "type": "bullish", "candle": "Latest", "reliability": "moderate"})

    # Hanging Man
    if (body_size(c0) > 0 and
            lower_wick(c0) >= 2 * body_size(c0) and
            upper_wick(c0) <= 0.3 * body_size(c0) and
            is_bearish(c0)):
        patterns.append({"pattern": "Hanging Man 🪢", "type": "bearish", "candle": "Latest", "reliability": "moderate"})

    # Marubozu Bullish
    if (is_bullish(c0) and
            body_size(c0) >= 0.9 * full_range(c0) and
            body_size(c0) >= 1.5 * avg_body):
        patterns.append({"pattern": "Bullish Marubozu 🟢", "type": "bullish", "candle": "Latest", "reliability": "high"})

    # Marubozu Bearish
    if (is_bearish(c0) and
            body_size(c0) >= 0.9 * full_range(c0) and
            body_size(c0) >= 1.5 * avg_body):
        patterns.append({"pattern": "Bearish Marubozu 🔴", "type": "bearish", "candle": "Latest", "reliability": "high"})

    # Spinning Top
    if (body_size(c0) > 0 and body_size(c0) < 0.3 * full_range(c0) and
            upper_wick(c0) > body_size(c0) and
            lower_wick(c0) > body_size(c0) and
            full_range(c0) > 0):
        patterns.append({"pattern": "Spinning Top 🌀", "type": "neutral", "candle": "Latest", "reliability": "low"})

    # ═══════════════════════════════════════════════════════
    # TWO CANDLE PATTERNS
    # ═══════════════════════════════════════════════════════

    # Bullish Engulfing
    if (is_bearish(c1) and is_bullish(c0) and
            c0["open"] < c1["close"] and c0["close"] > c1["open"]):
        patterns.append({"pattern": "Bullish Engulfing 🔥", "type": "bullish", "candle": "C0/C1", "reliability": "high"})

    # Bearish Engulfing
    if (is_bullish(c1) and is_bearish(c0) and
            c0["open"] > c1["close"] and c0["close"] < c1["open"]):
        patterns.append({"pattern": "Bearish Engulfing 💀", "type": "bearish", "candle": "C0/C1", "reliability": "high"})

    # Bullish Harami
    if (is_bearish(c1) and is_bullish(c0) and
            c0["open"] > c1["close"] and c0["close"] < c1["open"] and
            body_size(c0) < body_size(c1) * 0.5):
        patterns.append({"pattern": "Bullish Harami 🌱", "type": "bullish", "candle": "C0/C1", "reliability": "moderate"})

    # Bearish Harami
    if (is_bullish(c1) and is_bearish(c0) and
            c0["open"] < c1["close"] and c0["close"] > c1["open"] and
            body_size(c0) < body_size(c1) * 0.5):
        patterns.append({"pattern": "Bearish Harami 🍂", "type": "bearish", "candle": "C0/C1", "reliability": "moderate"})

    # Tweezer Top
    if (is_bullish(c1) and is_bearish(c0) and
            abs(c1["high"] - c0["high"]) / c1["high"] < 0.001):
        patterns.append({"pattern": "Tweezer Top 🏔️", "type": "bearish", "candle": "C0/C1", "reliability": "moderate"})

    # Tweezer Bottom
    if (is_bearish(c1) and is_bullish(c0) and
            abs(c1["low"] - c0["low"]) / c1["low"] < 0.001):
        patterns.append({"pattern": "Tweezer Bottom 🏝️", "type": "bullish", "candle": "C0/C1", "reliability": "moderate"})

    # Piercing Pattern (bullish)
    if (is_bearish(c1) and is_bullish(c0) and
            c0["open"] < c1["low"] and
            c0["close"] > body_mid(c1) and c0["close"] < c1["open"]):
        patterns.append({"pattern": "Piercing Pattern ⚡", "type": "bullish", "candle": "C0/C1", "reliability": "moderate"})

    # Dark Cloud Cover (bearish)
    if (is_bullish(c1) and is_bearish(c0) and
            c0["open"] > c1["high"] and
            c0["close"] < body_mid(c1) and c0["close"] > c1["open"]):
        patterns.append({"pattern": "Dark Cloud Cover 🌑", "type": "bearish", "candle": "C0/C1", "reliability": "moderate"})

    # Kicker Bullish
    if (is_bearish(c1) and is_bullish(c0) and
            c0["open"] >= c1["open"] and
            body_size(c0) > avg_body * 1.5):
        patterns.append({"pattern": "Bullish Kicker ⚡🟢", "type": "bullish", "candle": "C0/C1", "reliability": "very_high"})

    # Kicker Bearish
    if (is_bullish(c1) and is_bearish(c0) and
            c0["open"] <= c1["open"] and
            body_size(c0) > avg_body * 1.5):
        patterns.append({"pattern": "Bearish Kicker ⚡🔴", "type": "bearish", "candle": "C0/C1", "reliability": "very_high"})

    # ═══════════════════════════════════════════════════════
    # THREE CANDLE PATTERNS
    # ═══════════════════════════════════════════════════════

    # Morning Star
    if (is_bearish(c2) and
            body_size(c1) <= 0.3 * body_size(c2) and
            is_bullish(c0) and
            c0["close"] > (c2["open"] + c2["close"]) / 2):
        patterns.append({"pattern": "Morning Star 🌅", "type": "bullish", "candle": "C2/C1/C0", "reliability": "high"})

    # Evening Star
    if (is_bullish(c2) and
            body_size(c1) <= 0.3 * body_size(c2) and
            is_bearish(c0) and
            c0["close"] < (c2["open"] + c2["close"]) / 2):
        patterns.append({"pattern": "Evening Star 🌆", "type": "bearish", "candle": "C2/C1/C0", "reliability": "high"})

    # Three White Soldiers
    if (is_bullish(c2) and is_bullish(c1) and is_bullish(c0) and
            c1["close"] > c2["close"] and c0["close"] > c1["close"] and
            c1["open"] > c2["open"] and c0["open"] > c1["open"]):
        patterns.append({"pattern": "Three White Soldiers 🪖🪖🪖", "type": "bullish", "candle": "C2/C1/C0", "reliability": "very_high"})

    # Three Black Crows
    if (is_bearish(c2) and is_bearish(c1) and is_bearish(c0) and
            c1["close"] < c2["close"] and c0["close"] < c1["close"] and
            c1["open"] < c2["open"] and c0["open"] < c1["open"]):
        patterns.append({"pattern": "Three Black Crows 🐦‍⬛🐦‍⬛🐦‍⬛", "type": "bearish", "candle": "C2/C1/C0", "reliability": "very_high"})

    # Three Inside Up (Bullish)
    if (is_bearish(c2) and is_bullish(c1) and is_bullish(c0) and
            c1["open"] > c2["close"] and c1["close"] < c2["open"] and
            body_size(c1) < body_size(c2) * 0.5 and
            c0["close"] > c2["open"]):
        patterns.append({"pattern": "Three Inside Up 📈📈📈", "type": "bullish", "candle": "C2/C1/C0", "reliability": "high"})

    # Three Inside Down (Bearish)
    if (is_bullish(c2) and is_bearish(c1) and is_bearish(c0) and
            c1["open"] < c2["close"] and c1["close"] > c2["open"] and
            body_size(c1) < body_size(c2) * 0.5 and
            c0["close"] < c2["open"]):
        patterns.append({"pattern": "Three Inside Down 📉📉📉", "type": "bearish", "candle": "C2/C1/C0", "reliability": "high"})

    # Abandoned Baby Bullish
    if (is_bearish(c2) and is_bullish(c0) and
            body_size(c1) <= 0.1 * full_range(c1) and  # c1 is a doji
            c1["high"] < c2["low"] and  # Gap down
            c1["high"] < c0["low"]):     # Gap up
        patterns.append({"pattern": "Bullish Abandoned Baby 👶🟢", "type": "bullish", "candle": "C2/C1/C0", "reliability": "very_high"})

    # Abandoned Baby Bearish
    if (is_bullish(c2) and is_bearish(c0) and
            body_size(c1) <= 0.1 * full_range(c1) and
            c1["low"] > c2["high"] and
            c1["low"] > c0["high"]):
        patterns.append({"pattern": "Bearish Abandoned Baby 👶🔴", "type": "bearish", "candle": "C2/C1/C0", "reliability": "very_high"})

    return patterns
