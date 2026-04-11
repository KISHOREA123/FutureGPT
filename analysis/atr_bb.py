"""
ATR (Average True Range) + Bollinger Bands
ATR  → volatility measure, used for SL distance recommendations
BB   → squeeze detection (low volatility = potential big move incoming)
"""
import pandas as pd
import numpy as np


# ─────────────────────────────────────────────
# ATR
# ─────────────────────────────────────────────

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high  = df["high"]
    low   = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(span=period, adjust=False).mean()
    return atr


def get_atr_analysis(df: pd.DataFrame, period: int = 14) -> dict:
    """
    Returns ATR value, % of price, volatility label,
    and recommended SL distances (1x, 1.5x, 2x ATR).
    """
    atr    = calculate_atr(df, period)
    price  = float(df["close"].iloc[-1])
    atr_v  = float(atr.iloc[-1])
    atr_pct = round(atr_v / price * 100, 2)

    # Rolling ATR to judge relative volatility
    atr_avg = float(atr.tail(50).mean())
    ratio   = atr_v / atr_avg if atr_avg > 0 else 1.0

    if ratio > 1.5:
        vol_label = "High Volatility 🔥"
    elif ratio < 0.6:
        vol_label = "Low Volatility 😴"
    else:
        vol_label = "Normal Volatility ➡️"

    def fmt(v):
        if price >= 1000: return f"${v:,.2f}"
        elif price >= 1:  return f"${v:.4f}"
        else:             return f"${v:.6f}"

    return {
        "atr":         round(atr_v, 6),
        "atr_pct":     atr_pct,
        "volatility":  vol_label,
        "sl_1x":       fmt(price - atr_v),
        "sl_1x_short": fmt(price + atr_v),
        "sl_15x":      fmt(price - atr_v * 1.5),
        "sl_2x":       fmt(price - atr_v * 2),
        "sl_2x_short": fmt(price + atr_v * 2),
        "atr_ratio":   round(ratio, 2),
    }


# ─────────────────────────────────────────────
# BOLLINGER BANDS
# ─────────────────────────────────────────────

def calculate_bollinger_bands(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0
) -> dict:
    close  = df["close"]
    mid    = close.rolling(period).mean()
    std    = close.rolling(period).std()
    upper  = mid + std_dev * std
    lower  = mid - std_dev * std
    bw     = (upper - lower) / mid  # bandwidth
    return {"upper": upper, "mid": mid, "lower": lower, "bw": bw, "std": std}


def get_bb_analysis(df: pd.DataFrame, period: int = 20) -> dict:
    """
    Returns BB levels, squeeze detection, and price position within bands.
    Squeeze = bandwidth at multi-period low → breakout likely soon.
    """
    bands  = calculate_bollinger_bands(df, period)
    price  = float(df["close"].iloc[-1])
    upper  = float(bands["upper"].iloc[-1])
    mid    = float(bands["mid"].iloc[-1])
    lower  = float(bands["lower"].iloc[-1])
    bw     = float(bands["bw"].iloc[-1])

    # Squeeze: current bandwidth vs 50-candle average bandwidth
    bw_avg = float(bands["bw"].tail(50).mean())
    bw_min = float(bands["bw"].tail(50).min())
    squeeze_ratio = bw / bw_avg if bw_avg > 0 else 1.0

    # Squeeze level
    if bw <= bw_min * 1.1:
        squeeze = "🔴 Extreme Squeeze — Breakout imminent!"
    elif squeeze_ratio < 0.5:
        squeeze = "🟡 Squeeze Active — Low volatility, watch for breakout"
    else:
        squeeze = "No squeeze"

    # Price position
    band_range = upper - lower
    pct_b = (price - lower) / band_range if band_range > 0 else 0.5  # 0=lower, 1=upper

    if price > upper:
        position = "Above Upper Band 🔴 (Overbought / Breakout)"
    elif price < lower:
        position = "Below Lower Band 🟢 (Oversold / Breakdown)"
    elif pct_b > 0.8:
        position = "Near Upper Band ↑"
    elif pct_b < 0.2:
        position = "Near Lower Band ↓"
    else:
        position = "Mid-band ↔️"

    def fmt(v):
        if price >= 1000: return f"${v:,.2f}"
        elif price >= 1:  return f"${v:.4f}"
        else:             return f"${v:.6f}"

    return {
        "upper":         fmt(upper),
        "mid":           fmt(mid),
        "lower":         fmt(lower),
        "bandwidth_pct": round(bw * 100, 2),
        "squeeze":       squeeze,
        "position":      position,
        "pct_b":         round(pct_b * 100, 1),
        "squeeze_ratio": round(squeeze_ratio, 2),
    }
