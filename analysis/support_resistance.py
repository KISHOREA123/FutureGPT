import pandas as pd
import numpy as np
from config import SR_LOOKBACK, SR_TOUCH_TOLERANCE


def find_pivot_highs(df: pd.DataFrame, left: int = 5, right: int = 5) -> list:
    """Find pivot high points (local maxima)."""
    pivots = []
    for i in range(left, len(df) - right):
        window = df["high"].iloc[i - left: i + right + 1]
        if df["high"].iloc[i] == window.max():
            pivots.append((df.index[i], df["high"].iloc[i]))
    return pivots


def find_pivot_lows(df: pd.DataFrame, left: int = 5, right: int = 5) -> list:
    """Find pivot low points (local minima)."""
    pivots = []
    for i in range(left, len(df) - right):
        window = df["low"].iloc[i - left: i + right + 1]
        if df["low"].iloc[i] == window.min():
            pivots.append((df.index[i], df["low"].iloc[i]))
    return pivots


def cluster_levels(levels: list, tolerance: float = SR_TOUCH_TOLERANCE) -> list:
    """Cluster nearby price levels into single zones."""
    if not levels:
        return []
    sorted_levels = sorted(levels)
    clusters = []
    cluster = [sorted_levels[0]]

    for lvl in sorted_levels[1:]:
        if abs(lvl - cluster[-1]) / cluster[-1] <= tolerance:
            cluster.append(lvl)
        else:
            clusters.append(round(np.mean(cluster), 6))
            cluster = [lvl]
    clusters.append(round(np.mean(cluster), 6))
    return clusters


def count_touches(df: pd.DataFrame, level: float, tolerance: float = SR_TOUCH_TOLERANCE) -> int:
    """Count how many candles touched a level (high or low within tolerance)."""
    upper = level * (1 + tolerance)
    lower = level * (1 - tolerance)
    touches = ((df["high"] >= lower) & (df["high"] <= upper)) | \
              ((df["low"] >= lower) & (df["low"] <= upper))
    return int(touches.sum())


def get_support_resistance(df: pd.DataFrame, current_price: float) -> dict:
    """
    Main function: detect key support and resistance levels.
    Returns sorted support/resistance lists with touch counts and strength.
    """
    recent_df = df.tail(SR_LOOKBACK)

    # Get pivot highs & lows
    ph = [p[1] for p in find_pivot_highs(recent_df)]
    pl = [p[1] for p in find_pivot_lows(recent_df)]

    # Cluster them
    resistance_raw = cluster_levels([p for p in ph if p > current_price])
    support_raw = cluster_levels([p for p in pl if p < current_price])

    # Add touch counts and score
    resistance_levels = []
    for lvl in resistance_raw:
        touches = count_touches(df, lvl)
        strength = "Strong" if touches >= 3 else "Moderate" if touches == 2 else "Weak"
        resistance_levels.append({"level": lvl, "touches": touches, "strength": strength})

    support_levels = []
    for lvl in support_raw:
        touches = count_touches(df, lvl)
        strength = "Strong" if touches >= 3 else "Moderate" if touches == 2 else "Weak"
        support_levels.append({"level": lvl, "touches": touches, "strength": strength})

    # Sort: supports descending (closest first), resistances ascending (closest first)
    resistance_levels.sort(key=lambda x: x["level"])
    support_levels.sort(key=lambda x: x["level"], reverse=True)

    return {
        "support": support_levels[:5],
        "resistance": resistance_levels[:5],
        "nearest_support": support_levels[0] if support_levels else None,
        "nearest_resistance": resistance_levels[0] if resistance_levels else None,
    }
