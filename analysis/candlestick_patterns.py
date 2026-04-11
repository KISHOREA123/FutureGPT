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


def detect_patterns(df: pd.DataFrame) -> list:
    """Scan last 5 candles for known candlestick patterns. Returns list of detected patterns."""
    patterns = []
    n = len(df)
    if n < 3:
        return patterns

    c0 = df.iloc[-1]   # Latest candle
    c1 = df.iloc[-2]   # Previous candle
    c2 = df.iloc[-3]   # Two candles ago

    avg_body = df["close"].iloc[-10:].sub(df["open"].iloc[-10:]).abs().mean()

    # --- SINGLE CANDLE PATTERNS ---

    # Doji
    if body_size(c0) <= 0.1 * full_range(c0) and full_range(c0) > 0:
        patterns.append({"pattern": "Doji ⚪", "type": "neutral", "candle": "Latest"})

    # Hammer (bullish reversal at bottom)
    if (lower_wick(c0) >= 2 * body_size(c0) and
            upper_wick(c0) <= 0.3 * body_size(c0) and
            is_bullish(c0)):
        patterns.append({"pattern": "Hammer 🔨", "type": "bullish", "candle": "Latest"})

    # Shooting Star (bearish reversal at top)
    if (upper_wick(c0) >= 2 * body_size(c0) and
            lower_wick(c0) <= 0.3 * body_size(c0) and
            is_bearish(c0)):
        patterns.append({"pattern": "Shooting Star 💫", "type": "bearish", "candle": "Latest"})

    # Inverted Hammer
    if (upper_wick(c0) >= 2 * body_size(c0) and
            lower_wick(c0) <= 0.3 * body_size(c0) and
            is_bullish(c0)):
        patterns.append({"pattern": "Inverted Hammer 🔼", "type": "bullish", "candle": "Latest"})

    # Hanging Man
    if (lower_wick(c0) >= 2 * body_size(c0) and
            upper_wick(c0) <= 0.3 * body_size(c0) and
            is_bearish(c0)):
        patterns.append({"pattern": "Hanging Man 🪢", "type": "bearish", "candle": "Latest"})

    # Marubozu Bullish
    if (is_bullish(c0) and
            body_size(c0) >= 0.9 * full_range(c0) and
            body_size(c0) >= 1.5 * avg_body):
        patterns.append({"pattern": "Bullish Marubozu 🟢", "type": "bullish", "candle": "Latest"})

    # Marubozu Bearish
    if (is_bearish(c0) and
            body_size(c0) >= 0.9 * full_range(c0) and
            body_size(c0) >= 1.5 * avg_body):
        patterns.append({"pattern": "Bearish Marubozu 🔴", "type": "bearish", "candle": "Latest"})

    # --- TWO CANDLE PATTERNS ---

    # Bullish Engulfing
    if (is_bearish(c1) and is_bullish(c0) and
            c0["open"] < c1["close"] and c0["close"] > c1["open"]):
        patterns.append({"pattern": "Bullish Engulfing 🔥", "type": "bullish", "candle": "C0/C1"})

    # Bearish Engulfing
    if (is_bullish(c1) and is_bearish(c0) and
            c0["open"] > c1["close"] and c0["close"] < c1["open"]):
        patterns.append({"pattern": "Bearish Engulfing 💀", "type": "bearish", "candle": "C0/C1"})

    # Bullish Harami
    if (is_bearish(c1) and is_bullish(c0) and
            c0["open"] > c1["close"] and c0["close"] < c1["open"] and
            body_size(c0) < body_size(c1) * 0.5):
        patterns.append({"pattern": "Bullish Harami 🌱", "type": "bullish", "candle": "C0/C1"})

    # Bearish Harami
    if (is_bullish(c1) and is_bearish(c0) and
            c0["open"] < c1["close"] and c0["close"] > c1["open"] and
            body_size(c0) < body_size(c1) * 0.5):
        patterns.append({"pattern": "Bearish Harami 🍂", "type": "bearish", "candle": "C0/C1"})

    # Tweezer Top
    if (is_bullish(c1) and is_bearish(c0) and
            abs(c1["high"] - c0["high"]) / c1["high"] < 0.001):
        patterns.append({"pattern": "Tweezer Top 🏔️", "type": "bearish", "candle": "C0/C1"})

    # Tweezer Bottom
    if (is_bearish(c1) and is_bullish(c0) and
            abs(c1["low"] - c0["low"]) / c1["low"] < 0.001):
        patterns.append({"pattern": "Tweezer Bottom 🏝️", "type": "bullish", "candle": "C0/C1"})

    # --- THREE CANDLE PATTERNS ---

    # Morning Star
    if (is_bearish(c2) and
            body_size(c1) <= 0.3 * body_size(c2) and
            is_bullish(c0) and
            c0["close"] > (c2["open"] + c2["close"]) / 2):
        patterns.append({"pattern": "Morning Star 🌅", "type": "bullish", "candle": "C2/C1/C0"})

    # Evening Star
    if (is_bullish(c2) and
            body_size(c1) <= 0.3 * body_size(c2) and
            is_bearish(c0) and
            c0["close"] < (c2["open"] + c2["close"]) / 2):
        patterns.append({"pattern": "Evening Star 🌆", "type": "bearish", "candle": "C2/C1/C0"})

    # Three White Soldiers
    if (is_bullish(c2) and is_bullish(c1) and is_bullish(c0) and
            c1["close"] > c2["close"] and c0["close"] > c1["close"] and
            c1["open"] > c2["open"] and c0["open"] > c1["open"]):
        patterns.append({"pattern": "Three White Soldiers 🪖🪖🪖", "type": "bullish", "candle": "C2/C1/C0"})

    # Three Black Crows
    if (is_bearish(c2) and is_bearish(c1) and is_bearish(c0) and
            c1["close"] < c2["close"] and c0["close"] < c1["close"] and
            c1["open"] < c2["open"] and c0["open"] < c1["open"]):
        patterns.append({"pattern": "Three Black Crows 🐦‍⬛🐦‍⬛🐦‍⬛", "type": "bearish", "candle": "C2/C1/C0"})

    return patterns
