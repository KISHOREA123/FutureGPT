"""
Order Block Detection (Smart Money Concept)
An order block is the last bearish candle before a strong bullish move,
or the last bullish candle before a strong bearish move.
These zones represent areas where institutions placed large orders.
"""
import pandas as pd
import numpy as np


def detect_order_blocks(df: pd.DataFrame, lookback: int = 100, min_move_pct: float = 0.8) -> dict:
    """
    Detect bullish and bearish order blocks.

    Bullish OB:  Last bearish (red) candle before a strong upward impulse.
                 Price often returns to this zone to continue up.

    Bearish OB:  Last bullish (green) candle before a strong downward impulse.
                 Price often returns to this zone to continue down.

    min_move_pct: Minimum % move after the OB candle to qualify as an impulse.
    """
    recent = df.tail(lookback).copy()
    recent = recent.reset_index(drop=False)  # keep timestamp

    bullish_obs = []
    bearish_obs = []
    price = float(df["close"].iloc[-1])

    for i in range(2, len(recent) - 3):
        c   = recent.iloc[i]
        nxt = recent.iloc[i + 1]

        body   = abs(c["close"] - c["open"])
        rng    = c["high"] - c["low"]
        if rng == 0:
            continue

        # ── Bullish Order Block ─────────────────────────
        # Condition: bearish candle (close < open)
        # followed by a strong bullish impulse (next few candles move up significantly)
        if c["close"] < c["open"]:
            future_high = recent["high"].iloc[i+1 : i+5].max()
            move_pct    = (future_high - c["high"]) / c["high"] * 100
            if move_pct >= min_move_pct:
                ob_high = float(c["open"])   # top of bearish OB
                ob_low  = float(c["close"])  # bottom of bearish OB
                # Only include if price is still above OB (unmitigated)
                if price > ob_low:
                    bullish_obs.append({
                        "type":      "🟢 Bullish OB",
                        "high":      round(ob_high, 6),
                        "low":       round(ob_low, 6),
                        "mid":       round((ob_high + ob_low) / 2, 6),
                        "time":      str(recent["timestamp"].iloc[i])[:16] if "timestamp" in recent.columns else f"bar-{i}",
                        "move_pct":  round(move_pct, 2),
                        "mitigated": price < ob_high,   # price re-entered the OB
                        "status":    "🔄 Mitigated" if price < ob_high else "✅ Unmitigated",
                    })

        # ── Bearish Order Block ─────────────────────────
        # Condition: bullish candle (close > open)
        # followed by a strong bearish impulse
        if c["close"] > c["open"]:
            future_low  = recent["low"].iloc[i+1 : i+5].min()
            move_pct    = (c["low"] - future_low) / c["low"] * 100
            if move_pct >= min_move_pct:
                ob_high = float(c["close"])  # top of bullish OB
                ob_low  = float(c["open"])   # bottom of bullish OB
                # Only include if price is still below OB (unmitigated)
                if price < ob_high:
                    bearish_obs.append({
                        "type":      "🔴 Bearish OB",
                        "high":      round(ob_high, 6),
                        "low":       round(ob_low, 6),
                        "mid":       round((ob_high + ob_low) / 2, 6),
                        "time":      str(recent["timestamp"].iloc[i])[:16] if "timestamp" in recent.columns else f"bar-{i}",
                        "move_pct":  round(move_pct, 2),
                        "mitigated": price > ob_low,
                        "status":    "🔄 Mitigated" if price > ob_low else "✅ Unmitigated",
                    })

    # Sort by proximity to current price
    bullish_obs.sort(key=lambda x: abs(x["mid"] - price))
    bearish_obs.sort(key=lambda x: abs(x["mid"] - price))

    # Keep top 3 closest of each
    bullish_obs = bullish_obs[:3]
    bearish_obs = bearish_obs[:3]

    # Nearest OB of each type
    nearest_bull = bullish_obs[0] if bullish_obs else None
    nearest_bear = bearish_obs[0] if bearish_obs else None

    # Is price inside an OB right now?
    inside_bull = nearest_bull and (nearest_bull["low"] <= price <= nearest_bull["high"])
    inside_bear = nearest_bear and (nearest_bear["low"] <= price <= nearest_bear["high"])

    at_ob = None
    if inside_bull:
        at_ob = f"🟢 Price inside Bullish OB ({nearest_bull['low']} – {nearest_bull['high']})"
    elif inside_bear:
        at_ob = f"🔴 Price inside Bearish OB ({nearest_bear['low']} – {nearest_bear['high']})"

    return {
        "bullish_obs":   bullish_obs,
        "bearish_obs":   bearish_obs,
        "nearest_bull":  nearest_bull,
        "nearest_bear":  nearest_bear,
        "at_ob":         at_ob,
        "total_found":   len(bullish_obs) + len(bearish_obs),
    }
