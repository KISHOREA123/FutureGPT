"""
HTF (Higher Timeframe) Bias — Daily context
Fetches 1D candles and gives a clean macro trend snapshot:
  - EMA trend on daily
  - Market structure on daily
  - Key daily S/R (weekly pivots)
  - Daily candle character (bullish/bearish)
This is intentionally brief — just enough for directional context.
"""
import pandas as pd
import numpy as np


def get_daily_bias(df_daily: pd.DataFrame) -> dict:
    """
    Takes a daily OHLCV dataframe (50–100 candles).
    Returns a concise HTF bias summary.
    """
    close  = df_daily["close"]
    high   = df_daily["high"]
    low    = df_daily["low"]
    volume = df_daily["volume"]
    price  = float(close.iloc[-1])

    # ── Daily EMA trend ─────────────────────────────
    ema21  = float(close.ewm(span=21,  adjust=False).mean().iloc[-1])
    ema50  = float(close.ewm(span=50,  adjust=False).mean().iloc[-1])
    ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])

    if price > ema21 > ema50 > ema200:
        ema_trend = "Strong Uptrend 🚀"
        ema_bias  = "bullish"
    elif price < ema21 < ema50 < ema200:
        ema_trend = "Strong Downtrend 💥"
        ema_bias  = "bearish"
    elif price > ema200:
        ema_trend = "Above D-EMA200 📈"
        ema_bias  = "bullish"
    elif price < ema200:
        ema_trend = "Below D-EMA200 📉"
        ema_bias  = "bearish"
    else:
        ema_trend = "Mixed"
        ema_bias  = "neutral"

    # ── Daily structure (simple HH/LL on last 20 daily candles) ──
    recent  = df_daily.tail(20)
    recent_h = recent["high"].values
    recent_l = recent["low"].values

    structure = "Sideways"
    if len(recent_h) >= 4:
        if recent_h[-1] > recent_h[-3] and recent_l[-1] > recent_l[-3]:
            structure = "Higher Highs + Higher Lows (Uptrend)"
        elif recent_h[-1] < recent_h[-3] and recent_l[-1] < recent_l[-3]:
            structure = "Lower Highs + Lower Lows (Downtrend)"
        else:
            structure = "Choppy / Range"

    # ── Latest daily candle character ───────────────
    last = df_daily.iloc[-1]
    body = abs(last["close"] - last["open"])
    rng  = last["high"] - last["low"]
    body_pct = round(body / rng * 100, 1) if rng > 0 else 0
    candle_dir = "🟢 Bullish" if last["close"] > last["open"] else "🔴 Bearish"

    # Candle type
    if body_pct >= 70:
        candle_type = f"{candle_dir} Marubozu ({body_pct}% body)"
    elif body_pct <= 15:
        candle_type = "⚪ Doji / Indecision"
    else:
        candle_type = f"{candle_dir} ({body_pct}% body)"

    # ── Weekly high/low (last 7 daily candles) ──────
    week = df_daily.tail(7)
    weekly_high = round(float(week["high"].max()), 6)
    weekly_low  = round(float(week["low"].min()), 6)

    # ── Volume context ───────────────────────────────
    avg_vol = float(volume.tail(20).mean())
    last_vol = float(volume.iloc[-1])
    vol_note = "Above avg 📊" if last_vol > avg_vol * 1.2 else (
               "Below avg 📉" if last_vol < avg_vol * 0.8 else "Average ➡️")

    # ── Overall bias label ───────────────────────────
    if ema_bias == "bullish" and "Uptrend" in structure:
        bias_label = "🟢 BULLISH"
    elif ema_bias == "bearish" and "Downtrend" in structure:
        bias_label = "🔴 BEARISH"
    elif ema_bias == "bullish":
        bias_label = "📗 Weak Bullish"
    elif ema_bias == "bearish":
        bias_label = "📕 Weak Bearish"
    else:
        bias_label = "⚪ Neutral"

    def fmt(v):
        if price >= 1000: return f"${v:,.2f}"
        elif price >= 1:  return f"${v:.4f}"
        else:             return f"${v:.6f}"

    return {
        "price":        fmt(price),
        "bias":         bias_label,
        "ema_trend":    ema_trend,
        "ema21":        fmt(ema21),
        "ema50":        fmt(ema50),
        "ema200":       fmt(ema200),
        "structure":    structure,
        "candle":       candle_type,
        "weekly_high":  fmt(weekly_high),
        "weekly_low":   fmt(weekly_low),
        "volume":       vol_note,
    }
