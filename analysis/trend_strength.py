"""
Trend Strength Analysis — ADX + EMA Slope + Momentum Quality
Provides a comprehensive trend quality score to supplement confluence.
"""
import pandas as pd
import numpy as np
from config import ADX_PERIOD, ADX_STRONG_TREND, ADX_WEAK_TREND


def calculate_adx(df: pd.DataFrame, period: int = ADX_PERIOD) -> dict:
    """
    Calculate ADX (Average Directional Index) + DI+ / DI-.
    ADX measures trend STRENGTH (not direction).
      > 25 = Strong trend
      15-25 = Weak trend
      < 15 = No trend / Ranging
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # +DM / -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    # True Range
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Smoothed averages
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

    # DX and ADX
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1))
    adx = dx.ewm(span=period, adjust=False).mean()

    adx_val = round(float(adx.iloc[-1]), 2)
    plus_di_val = round(float(plus_di.iloc[-1]), 2)
    minus_di_val = round(float(minus_di.iloc[-1]), 2)
    prev_adx = round(float(adx.iloc[-2]), 2)

    # Trend strength label
    if adx_val >= ADX_STRONG_TREND:
        strength = "Strong Trend 💪"
    elif adx_val >= ADX_WEAK_TREND:
        strength = "Weak Trend ➡️"
    else:
        strength = "No Trend / Ranging 😴"

    # ADX direction (rising = trend strengthening)
    adx_rising = adx_val > prev_adx
    direction_note = "ADX Rising ↑ (trend strengthening)" if adx_rising else "ADX Falling ↓ (trend weakening)"

    # DI crossover
    di_cross = "None"
    prev_plus = float(plus_di.iloc[-2])
    prev_minus = float(minus_di.iloc[-2])
    if plus_di_val > minus_di_val and prev_plus <= prev_minus:
        di_cross = "🟢 DI+ crossed above DI- (Bullish)"
    elif minus_di_val > plus_di_val and prev_minus <= prev_plus:
        di_cross = "🔴 DI- crossed above DI+ (Bearish)"

    return {
        "adx": adx_val,
        "plus_di": plus_di_val,
        "minus_di": minus_di_val,
        "strength": strength,
        "direction": direction_note,
        "adx_rising": adx_rising,
        "di_cross": di_cross,
    }


def calculate_ema_slope(df: pd.DataFrame, ema_period: int = 21, slope_lookback: int = 5) -> dict:
    """
    Measure EMA slope (rate of change) to detect trend acceleration.
    Positive slope = price accelerating up.
    Negative slope = price accelerating down.
    """
    ema = df["close"].ewm(span=ema_period, adjust=False).mean()
    slope = (ema.iloc[-1] - ema.iloc[-slope_lookback]) / ema.iloc[-slope_lookback] * 100

    if slope > 1.0:
        label = "Strong Upward Momentum 🚀"
    elif slope > 0.3:
        label = "Mild Upward Drift ↗️"
    elif slope > -0.3:
        label = "Flat / Sideways ↔️"
    elif slope > -1.0:
        label = "Mild Downward Drift ↘️"
    else:
        label = "Strong Downward Momentum 💥"

    return {
        "slope_pct": round(slope, 3),
        "label": label,
    }


def get_trend_strength(df: pd.DataFrame) -> dict:
    """
    Master function: combines ADX + EMA slope into a single trend quality verdict.
    Returns trend_score (0-100), label, and components.
    """
    adx_data = calculate_adx(df)
    slope_data = calculate_ema_slope(df)

    adx_val = adx_data["adx"]
    slope_val = abs(slope_data["slope_pct"])

    # Trend score: weighted blend of ADX and slope magnitude
    # ADX is 0-100, slope we normalize to 0-100 range (cap at 3%)
    slope_norm = min(slope_val / 3.0, 1.0) * 100
    trend_score = round(adx_val * 0.6 + slope_norm * 0.4, 1)
    trend_score = min(100, max(0, trend_score))

    # Final label
    if trend_score >= 70:
        quality = "Excellent Trend Quality ✅"
    elif trend_score >= 45:
        quality = "Moderate Trend Quality ⚠️"
    elif trend_score >= 25:
        quality = "Weak Trend Quality 🔸"
    else:
        quality = "Choppy / No Clear Trend ❌"

    return {
        "trend_score": trend_score,
        "quality": quality,
        "adx": adx_data,
        "ema_slope": slope_data,
    }
