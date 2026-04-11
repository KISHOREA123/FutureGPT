"""
Fair Value Gap (FVG) — ICT Concept
A Fair Value Gap is a 3-candle pattern where:
  - Bullish FVG: candle[i-1].high < candle[i+1].low  → gap between two candles (price moved up too fast)
  - Bearish FVG: candle[i-1].low  > candle[i+1].high → gap below (price moved down too fast)

Price tends to return to fill these imbalance zones.
"""
import pandas as pd
import numpy as np


def detect_fvg(df: pd.DataFrame, lookback: int = 80) -> dict:
    """
    Scan recent candles for Fair Value Gaps.
    Returns bullish and bearish FVGs sorted by proximity to current price.
    """
    recent  = df.tail(lookback).reset_index(drop=False)
    price   = float(df["close"].iloc[-1])

    bullish_fvgs = []
    bearish_fvgs = []

    for i in range(1, len(recent) - 1):
        prev = recent.iloc[i - 1]
        curr = recent.iloc[i]
        nxt  = recent.iloc[i + 1]

        # ── Bullish FVG ─────────────────────────────
        # Gap: previous candle high < next candle low
        if prev["high"] < nxt["low"]:
            gap_high = float(nxt["low"])
            gap_low  = float(prev["high"])
            gap_size = gap_high - gap_low
            gap_pct  = round(gap_size / gap_low * 100, 2)

            # Skip tiny gaps (< 0.05%)
            if gap_pct < 0.05:
                continue

            # Is it still open (price hasn't filled it)?
            filled = price <= gap_high and price >= gap_low  # price is inside
            fully_filled = price < gap_low                    # price came back down through it

            if not fully_filled:  # show open + partial fills only
                time_str = str(recent["timestamp"].iloc[i])[:16] if "timestamp" in recent.columns else f"bar-{i}"
                bullish_fvgs.append({
                    "type":     "🟢 Bullish FVG",
                    "high":     round(gap_high, 6),
                    "low":      round(gap_low, 6),
                    "mid":      round((gap_high + gap_low) / 2, 6),
                    "gap_pct":  gap_pct,
                    "time":     time_str,
                    "status":   "🔄 Partially Filled" if filled else "✅ Open",
                    "filled":   filled,
                })

        # ── Bearish FVG ─────────────────────────────
        # Gap: previous candle low > next candle high
        if prev["low"] > nxt["high"]:
            gap_high = float(prev["low"])
            gap_low  = float(nxt["high"])
            gap_size = gap_high - gap_low
            gap_pct  = round(gap_size / gap_low * 100, 2)

            if gap_pct < 0.05:
                continue

            filled       = price >= gap_low and price <= gap_high
            fully_filled = price > gap_high

            if not fully_filled:
                time_str = str(recent["timestamp"].iloc[i])[:16] if "timestamp" in recent.columns else f"bar-{i}"
                bearish_fvgs.append({
                    "type":     "🔴 Bearish FVG",
                    "high":     round(gap_high, 6),
                    "low":      round(gap_low, 6),
                    "mid":      round((gap_high + gap_low) / 2, 6),
                    "gap_pct":  gap_pct,
                    "time":     time_str,
                    "status":   "🔄 Partially Filled" if filled else "✅ Open",
                    "filled":   filled,
                })

    # Sort by proximity to current price
    bullish_fvgs.sort(key=lambda x: abs(x["mid"] - price))
    bearish_fvgs.sort(key=lambda x: abs(x["mid"] - price))

    # Keep top 3 of each
    bullish_fvgs = bullish_fvgs[:3]
    bearish_fvgs = bearish_fvgs[:3]

    # Is price currently sitting inside an FVG?
    at_fvg = None
    for fvg in bullish_fvgs + bearish_fvgs:
        if fvg["low"] <= price <= fvg["high"]:
            at_fvg = f"{fvg['type']} ({fvg['low']} – {fvg['high']})"
            break

    # Nearest above and below
    above = [f for f in bearish_fvgs if f["mid"] > price]
    below = [f for f in bullish_fvgs if f["mid"] < price]

    return {
        "bullish_fvgs":  bullish_fvgs,
        "bearish_fvgs":  bearish_fvgs,
        "nearest_above": above[0] if above else None,
        "nearest_below": below[0] if below else None,
        "at_fvg":        at_fvg,
        "total_open":    len(bullish_fvgs) + len(bearish_fvgs),
    }
