import pandas as pd
import numpy as np
from config import LIQUIDITY_EQUAL_TOLERANCE


def find_equal_highs(df: pd.DataFrame, lookback: int = 50) -> list:
    """Find equal highs (potential buy-side liquidity)."""
    recent = df.tail(lookback)
    highs = recent["high"].values
    equal_highs = []

    for i in range(len(highs)):
        for j in range(i + 3, len(highs)):  # at least 3 candles apart
            diff = abs(highs[i] - highs[j]) / highs[i]
            if diff <= LIQUIDITY_EQUAL_TOLERANCE:
                equal_highs.append(round((highs[i] + highs[j]) / 2, 6))

    # Deduplicate clusters
    if not equal_highs:
        return []
    equal_highs.sort()
    result = [equal_highs[0]]
    for lvl in equal_highs[1:]:
        if abs(lvl - result[-1]) / result[-1] > LIQUIDITY_EQUAL_TOLERANCE * 2:
            result.append(lvl)
    return result


def find_equal_lows(df: pd.DataFrame, lookback: int = 50) -> list:
    """Find equal lows (potential sell-side liquidity)."""
    recent = df.tail(lookback)
    lows = recent["low"].values
    equal_lows = []

    for i in range(len(lows)):
        for j in range(i + 3, len(lows)):
            diff = abs(lows[i] - lows[j]) / lows[i]
            if diff <= LIQUIDITY_EQUAL_TOLERANCE:
                equal_lows.append(round((lows[i] + lows[j]) / 2, 6))

    if not equal_lows:
        return []
    equal_lows.sort()
    result = [equal_lows[0]]
    for lvl in equal_lows[1:]:
        if abs(lvl - result[-1]) / result[-1] > LIQUIDITY_EQUAL_TOLERANCE * 2:
            result.append(lvl)
    return result


def detect_stop_hunt(df: pd.DataFrame, lookback: int = 30) -> list:
    """
    Detect potential stop hunts: candle wick pierces a key level
    then closes back above/below it (wick rejection).
    """
    recent = df.tail(lookback)
    hunts = []

    for i in range(2, len(recent)):
        c = recent.iloc[i]
        prev_lows = recent["low"].iloc[:i].min()
        prev_highs = recent["high"].iloc[:i].max()

        # Bullish stop hunt: wick below recent low, closes back above
        if c["low"] < prev_lows and c["close"] > prev_lows:
            hunts.append({
                "type": "🟢 Bullish Stop Hunt",
                "price": round(c["low"], 6),
                "time": recent.index[i].strftime("%Y-%m-%d %H:%M"),
                "note": "Wick swept below swing low, closed above"
            })

        # Bearish stop hunt: wick above recent high, closes back below
        if c["high"] > prev_highs and c["close"] < prev_highs:
            hunts.append({
                "type": "🔴 Bearish Stop Hunt",
                "price": round(c["high"], 6),
                "time": recent.index[i].strftime("%Y-%m-%d %H:%M"),
                "note": "Wick swept above swing high, closed below"
            })

    return hunts[-3:] if hunts else []  # Return last 3 only


def get_liquidity_zones(df: pd.DataFrame, current_price: float) -> dict:
    """Main function: compile all liquidity analysis."""
    eq_highs = find_equal_highs(df)
    eq_lows = find_equal_lows(df)
    stop_hunts = detect_stop_hunt(df)

    # Separate into above/below current price
    buy_side = [h for h in eq_highs if h > current_price]
    sell_side = [l for l in eq_lows if l < current_price]

    # Sort closest first
    buy_side.sort()
    sell_side.sort(reverse=True)

    return {
        "buy_side_liquidity": buy_side[:4],    # Equal highs above price (stops of shorts)
        "sell_side_liquidity": sell_side[:4],  # Equal lows below price (stops of longs)
        "stop_hunts": stop_hunts,
        "nearest_buy_liq": buy_side[0] if buy_side else None,
        "nearest_sell_liq": sell_side[0] if sell_side else None,
    }
