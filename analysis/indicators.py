import pandas as pd
import numpy as np
from config import (
    EMA_FAST, EMA_SLOW, EMA_TREND,
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL
)


def calculate_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = series.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = series.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_emas(series: pd.Series) -> dict:
    return {
        "ema_fast": series.ewm(span=EMA_FAST, adjust=False).mean(),
        "ema_slow": series.ewm(span=EMA_SLOW, adjust=False).mean(),
        "ema_trend": series.ewm(span=EMA_TREND, adjust=False).mean(),
    }


def get_volume_trend(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Analyze volume trend: rising/falling, spike detection."""
    recent = df["volume"].tail(lookback)
    avg_vol = recent.mean()
    latest_vol = df["volume"].iloc[-1]
    prev_vol = df["volume"].iloc[-2]

    # Rising or falling volume over last N candles
    vol_ma5 = df["volume"].tail(5).mean()
    vol_ma20 = avg_vol

    if vol_ma5 > vol_ma20 * 1.2:
        trend = "Rising Volume 📊 (Momentum building)"
    elif vol_ma5 < vol_ma20 * 0.8:
        trend = "Declining Volume 📉 (Weak momentum)"
    else:
        trend = "Average Volume ➡️ (Neutral)"

    # Spike detection
    is_spike = latest_vol > avg_vol * 2.0
    spike_note = f"⚡ Volume Spike! ({latest_vol/avg_vol:.1f}x avg)" if is_spike else "No spike"

    # Climax candle check (huge candle + huge volume)
    latest_body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    avg_body = df["close"].tail(20).sub(df["open"].tail(20)).abs().mean()
    is_climax = is_spike and latest_body > avg_body * 1.5

    return {
        "trend": trend,
        "spike": spike_note,
        "latest_volume": round(latest_vol, 2),
        "avg_volume_20": round(avg_vol, 2),
        "volume_ratio": round(latest_vol / avg_vol, 2),
        "climax_candle": "⚠️ Possible Climax Candle!" if is_climax else "No climax",
    }


def get_rsi_analysis(rsi_series: pd.Series) -> dict:
    rsi_val = round(rsi_series.iloc[-1], 2)
    prev_rsi = round(rsi_series.iloc[-2], 2)

    if rsi_val >= RSI_OVERBOUGHT:
        zone = "Overbought 🔴"
    elif rsi_val <= RSI_OVERSOLD:
        zone = "Oversold 🟢"
    elif rsi_val > 55:
        zone = "Bullish Zone"
    elif rsi_val < 45:
        zone = "Bearish Zone"
    else:
        zone = "Neutral Zone"

    direction = "Rising ↑" if rsi_val > prev_rsi else "Falling ↓"

    # Hidden / Regular Divergence hints (simple version)
    divergence = "None detected"

    return {
        "value": rsi_val,
        "zone": zone,
        "direction": direction,
        "divergence": divergence,
    }


def get_macd_analysis(macd: pd.Series, signal: pd.Series, hist: pd.Series) -> dict:
    macd_val = round(macd.iloc[-1], 6)
    signal_val = round(signal.iloc[-1], 6)
    hist_val = round(hist.iloc[-1], 6)
    prev_hist = round(hist.iloc[-2], 6)

    # Crossover detection
    crossover = "None"
    if hist_val > 0 and prev_hist <= 0:
        crossover = "🟢 Bullish Crossover (MACD crossed above Signal)"
    elif hist_val < 0 and prev_hist >= 0:
        crossover = "🔴 Bearish Crossover (MACD crossed below Signal)"

    momentum = "Bullish momentum" if macd_val > 0 else "Bearish momentum"
    hist_trend = "Increasing" if abs(hist_val) > abs(prev_hist) else "Decreasing"

    return {
        "macd": macd_val,
        "signal": signal_val,
        "histogram": hist_val,
        "crossover": crossover,
        "momentum": momentum,
        "histogram_trend": hist_trend,
    }


def get_ema_analysis(df: pd.DataFrame, emas: dict) -> dict:
    price = df["close"].iloc[-1]
    ema21 = round(emas["ema_fast"].iloc[-1], 6)
    ema55 = round(emas["ema_slow"].iloc[-1], 6)
    ema200 = round(emas["ema_trend"].iloc[-1], 6)

    # Price vs EMAs
    if price > ema21 > ema55 > ema200:
        trend = "Strong Uptrend 🚀 (Price > EMA21 > EMA55 > EMA200)"
    elif price < ema21 < ema55 < ema200:
        trend = "Strong Downtrend 💥 (Price < EMA21 < EMA55 < EMA200)"
    elif price > ema200:
        trend = "Above EMA200 - Bullish Bias 📈"
    elif price < ema200:
        trend = "Below EMA200 - Bearish Bias 📉"
    else:
        trend = "Mixed EMA signals ↔️"

    # Golden/Death cross (EMA21 vs EMA55)
    prev_ema21 = emas["ema_fast"].iloc[-2]
    prev_ema55 = emas["ema_slow"].iloc[-2]
    cross = "None"
    if ema21 > ema55 and prev_ema21 <= prev_ema55:
        cross = "🌟 Golden Cross (EMA21 crossed above EMA55)"
    elif ema21 < ema55 and prev_ema21 >= prev_ema55:
        cross = "💀 Death Cross (EMA21 crossed below EMA55)"

    return {
        "trend": trend,
        "ema21": ema21,
        "ema55": ema55,
        "ema200": ema200,
        "cross": cross,
    }


def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> dict:
    """Stochastic Oscillator — %K and %D for momentum analysis."""
    from config import STOCH_OVERBOUGHT, STOCH_OVERSOLD

    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    denom = high_max - low_min
    denom = denom.replace(0, 1)

    k_line = 100 * (df["close"] - low_min) / denom
    d_line = k_line.rolling(d_period).mean()

    k_val = round(float(k_line.iloc[-1]), 2)
    d_val = round(float(d_line.iloc[-1]), 2)
    prev_k = round(float(k_line.iloc[-2]), 2)
    prev_d = round(float(d_line.iloc[-2]), 2)

    # Zone
    if k_val >= STOCH_OVERBOUGHT:
        zone = "Overbought 🔴"
    elif k_val <= STOCH_OVERSOLD:
        zone = "Oversold 🟢"
    else:
        zone = "Neutral"

    # Crossover
    cross = "None"
    if k_val > d_val and prev_k <= prev_d:
        cross = "🟢 Bullish Crossover (%K above %D)"
    elif k_val < d_val and prev_k >= prev_d:
        cross = "🔴 Bearish Crossover (%K below %D)"

    return {
        "k": k_val,
        "d": d_val,
        "zone": zone,
        "cross": cross,
    }


def run_indicators(df: pd.DataFrame) -> dict:
    """Run all indicators and return compiled results."""
    rsi = calculate_rsi(df["close"])
    macd_line, signal_line, histogram = calculate_macd(df["close"])
    emas = calculate_emas(df["close"])

    return {
        "rsi": get_rsi_analysis(rsi),
        "macd": get_macd_analysis(macd_line, signal_line, histogram),
        "ema": get_ema_analysis(df, emas),
        "volume": get_volume_trend(df),
        "stochastic": calculate_stochastic(df),
    }

