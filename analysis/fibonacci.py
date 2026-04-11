import pandas as pd
import numpy as np


FIBO_RATIOS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
FIBO_EXTENSIONS = [1.272, 1.414, 1.618, 2.0, 2.618]


def find_last_major_swing(df: pd.DataFrame, lookback: int = 100) -> tuple:
    """
    Find the most recent significant swing high and swing low
    within the lookback window to draw Fibonacci from.
    Returns (swing_low_price, swing_high_price, direction)
    direction = 'up' means price moved up (low -> high), 'down' = high -> low
    """
    recent = df.tail(lookback)
    swing_high_idx = recent["high"].idxmax()
    swing_low_idx = recent["low"].idxmin()

    swing_high = float(recent["high"].max())
    swing_low = float(recent["low"].min())

    # Determine direction: which came first?
    high_pos = recent.index.get_loc(swing_high_idx)
    low_pos = recent.index.get_loc(swing_low_idx)

    if low_pos < high_pos:
        # Low happened first → price moved UP → retracement goes downward
        direction = "up"
    else:
        # High happened first → price moved DOWN → retracement goes upward
        direction = "down"

    return swing_low, swing_high, direction


def calculate_fibonacci(df: pd.DataFrame, lookback: int = 100) -> dict:
    """
    Calculate Fibonacci retracement and extension levels.
    Returns levels dict with prices and proximity to current price.
    """
    swing_low, swing_high, direction = find_last_major_swing(df, lookback)
    current_price = float(df["close"].iloc[-1])
    diff = swing_high - swing_low

    # Retracement levels (between swing high and low)
    if direction == "up":
        # Retracement FROM high (potential support zones on pullback)
        retracement = {
            f"{int(r*100)}%" if r not in (0.0, 1.0) else ("0% (High)" if r == 0.0 else "100% (Low)"):
            round(swing_high - diff * r, 6)
            for r in FIBO_RATIOS
        }
        # Extension levels (above the swing high - targets)
        extensions = {
            f"{int(e*100)}% Ext": round(swing_low + diff * e, 6)
            for e in FIBO_EXTENSIONS
        }
    else:
        # Retracement FROM low (potential resistance zones on bounce)
        retracement = {
            f"{int(r*100)}%" if r not in (0.0, 1.0) else ("0% (Low)" if r == 0.0 else "100% (High)"):
            round(swing_low + diff * r, 6)
            for r in FIBO_RATIOS
        }
        extensions = {
            f"{int(e*100)}% Ext": round(swing_high - diff * (e - 1.0), 6)
            for e in FIBO_EXTENSIONS
        }

    # Find nearest fib level to current price
    all_levels = {**retracement}
    nearest_label = min(all_levels, key=lambda k: abs(all_levels[k] - current_price))
    nearest_price = all_levels[nearest_label]
    proximity_pct = round(abs(current_price - nearest_price) / current_price * 100, 2)

    # Is price at a golden zone? (0.618 or 0.5 ± 1%)
    golden_zone = False
    for label, price in all_levels.items():
        if ("61" in label or "50%" in label) and abs(current_price - price) / current_price < 0.01:
            golden_zone = True
            break

    return {
        "swing_high": swing_high,
        "swing_low": swing_low,
        "direction": direction,
        "retracement_levels": retracement,
        "extension_levels": extensions,
        "nearest_level": nearest_label,
        "nearest_price": nearest_price,
        "proximity_pct": proximity_pct,
        "golden_zone": golden_zone,
    }
