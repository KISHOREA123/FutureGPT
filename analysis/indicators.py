"""
Technical Indicators Module — Enhanced v2.0
Computes 21 technical indicators for comprehensive market analysis.
"""
import pandas as pd
import numpy as np
from config import (
    EMA_FAST, EMA_SLOW, EMA_TREND, EMA_SHORT, EMA_MID, EMA_LONG,
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    STOCH_K_PERIOD, STOCH_D_PERIOD, STOCH_OVERBOUGHT, STOCH_OVERSOLD,
    BB_PERIOD, BB_STD, ATR_PERIOD, ADX_PERIOD, VOLUME_MA_PERIOD,
    ICHIMOKU_TENKAN, ICHIMOKU_KIJUN, ICHIMOKU_SENKOU_B,
    SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER,
)


# ═══════════════════════════════════════════════════════════════
# CORE INDICATOR CALCULATORS (used by other modules too)
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# NEW: FULL INDICATOR COMPUTATION (for ML / Strategy Engine)
# ═══════════════════════════════════════════════════════════════

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute ALL 21 technical indicators and add as columns to the DataFrame."""
    df = df.copy()
    df = _compute_moving_averages(df)
    df = _compute_rsi(df)
    df = _compute_macd(df)
    df = _compute_bollinger_bands(df)
    df = _compute_stochastic(df)
    df = _compute_atr(df)
    df = _compute_adx(df)
    df = _compute_volume_indicators(df)
    df = _compute_ichimoku(df)
    df = _compute_supertrend(df)
    df = _compute_vwap(df)
    df = _compute_obv(df)
    df = _compute_cci(df)
    df = _compute_williams_r(df)
    df = _compute_mfi(df)
    df = _compute_pivot_points(df)
    df = _compute_keltner_channels(df)
    df = _compute_chaikin_money_flow(df)
    return df


def _compute_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df["ema_9"] = df["close"].ewm(span=EMA_SHORT, adjust=False).mean()
    df["ema_21"] = df["close"].ewm(span=EMA_MID, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=EMA_LONG, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=EMA_TREND, adjust=False).mean()
    df["sma_20"] = df["close"].rolling(window=20).mean()
    df["sma_50"] = df["close"].rolling(window=50).mean()
    df["sma_200"] = df["close"].rolling(window=200).mean()
    return df


def _compute_rsi(df: pd.DataFrame) -> pd.DataFrame:
    period = RSI_PERIOD
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi_sma"] = df["rsi"].rolling(window=14).mean()
    return df


def _compute_macd(df: pd.DataFrame) -> pd.DataFrame:
    ema_fast = df["close"].ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = df["close"].ewm(span=MACD_SLOW, adjust=False).mean()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]
    return df


def _compute_bollinger_bands(df: pd.DataFrame) -> pd.DataFrame:
    df["bb_middle"] = df["close"].rolling(window=BB_PERIOD).mean()
    bb_std = df["close"].rolling(window=BB_PERIOD).std()
    df["bb_upper"] = df["bb_middle"] + (BB_STD * bb_std)
    df["bb_lower"] = df["bb_middle"] - (BB_STD * bb_std)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
    df["bb_percent"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    return df


def _compute_stochastic(df: pd.DataFrame) -> pd.DataFrame:
    low_min = df["low"].rolling(window=STOCH_K_PERIOD).min()
    high_max = df["high"].rolling(window=STOCH_K_PERIOD).max()
    df["stoch_k"] = 100 * (df["close"] - low_min) / (high_max - low_min)
    df["stoch_d"] = df["stoch_k"].rolling(window=STOCH_D_PERIOD).mean()
    return df


def _compute_atr(df: pd.DataFrame) -> pd.DataFrame:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = true_range.rolling(window=ATR_PERIOD).mean()
    df["atr_percent"] = (df["atr"] / df["close"]) * 100
    return df


def _compute_adx(df: pd.DataFrame) -> pd.DataFrame:
    period = ADX_PERIOD
    plus_dm = df["high"].diff()
    minus_dm = -df["low"].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    atr_val = tr.ewm(alpha=1 / period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr_val)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr_val)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    df["adx"] = dx.ewm(alpha=1 / period, min_periods=period).mean()
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di
    return df


def _compute_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df["volume_sma"] = df["volume"].rolling(window=VOLUME_MA_PERIOD).mean()
    df["volume_ratio"] = df["volume"] / df["volume_sma"]
    df["volume_ema"] = df["volume"].ewm(span=VOLUME_MA_PERIOD, adjust=False).mean()
    df["volume_trend"] = (
        df["volume"].rolling(window=5).mean()
        / df["volume"].rolling(window=20).mean()
    )
    return df


def _compute_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    tenkan_high = df["high"].rolling(window=ICHIMOKU_TENKAN).max()
    tenkan_low = df["low"].rolling(window=ICHIMOKU_TENKAN).min()
    df["ichimoku_tenkan"] = (tenkan_high + tenkan_low) / 2

    kijun_high = df["high"].rolling(window=ICHIMOKU_KIJUN).max()
    kijun_low = df["low"].rolling(window=ICHIMOKU_KIJUN).min()
    df["ichimoku_kijun"] = (kijun_high + kijun_low) / 2

    df["ichimoku_senkou_a"] = (
        (df["ichimoku_tenkan"] + df["ichimoku_kijun"]) / 2
    ).shift(ICHIMOKU_KIJUN)

    senkou_b_high = df["high"].rolling(window=ICHIMOKU_SENKOU_B).max()
    senkou_b_low = df["low"].rolling(window=ICHIMOKU_SENKOU_B).min()
    df["ichimoku_senkou_b"] = ((senkou_b_high + senkou_b_low) / 2).shift(ICHIMOKU_KIJUN)

    df["ichimoku_chikou"] = df["close"].shift(-ICHIMOKU_KIJUN)
    return df


def _compute_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    period = SUPERTREND_PERIOD
    multiplier = SUPERTREND_MULTIPLIER
    hl2 = (df["high"] + df["low"]) / 2

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=float)
    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(df)):
        if df["close"].iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df["close"].iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
            if direction.iloc[i] == 1 and lower_band.iloc[i] < lower_band.iloc[i - 1]:
                lower_band.iloc[i] = lower_band.iloc[i - 1]
            if direction.iloc[i] == -1 and upper_band.iloc[i] > upper_band.iloc[i - 1]:
                upper_band.iloc[i] = upper_band.iloc[i - 1]

        supertrend.iloc[i] = (
            lower_band.iloc[i] if direction.iloc[i] == 1 else upper_band.iloc[i]
        )

    df["supertrend"] = supertrend
    df["supertrend_direction"] = direction
    return df


def _compute_vwap(df: pd.DataFrame) -> pd.DataFrame:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    df["vwap"] = cumulative_tp_vol / cumulative_vol
    return df


def _compute_obv(df: pd.DataFrame) -> pd.DataFrame:
    obv = pd.Series(index=df.index, dtype=float)
    obv.iloc[0] = 0
    for i in range(1, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + df["volume"].iloc[i]
        elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - df["volume"].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]
    df["obv"] = obv
    df["obv_sma"] = df["obv"].rolling(window=20).mean()
    return df


def _compute_cci(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    sma = typical_price.rolling(window=period).mean()
    mad = typical_price.rolling(window=period).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    df["cci"] = (typical_price - sma) / (0.015 * mad)
    return df


def _compute_williams_r(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    highest_high = df["high"].rolling(window=period).max()
    lowest_low = df["low"].rolling(window=period).min()
    df["williams_r"] = -100 * (highest_high - df["close"]) / (highest_high - lowest_low)
    return df


def _compute_mfi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    raw_money_flow = typical_price * df["volume"]
    positive_flow = pd.Series(0.0, index=df.index)
    negative_flow = pd.Series(0.0, index=df.index)

    for i in range(1, len(df)):
        if typical_price.iloc[i] > typical_price.iloc[i - 1]:
            positive_flow.iloc[i] = raw_money_flow.iloc[i]
        elif typical_price.iloc[i] < typical_price.iloc[i - 1]:
            negative_flow.iloc[i] = raw_money_flow.iloc[i]

    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    money_ratio = positive_mf / negative_mf
    df["mfi"] = 100 - (100 / (1 + money_ratio))
    return df


def _compute_pivot_points(df: pd.DataFrame) -> pd.DataFrame:
    df["pivot"] = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3
    df["pivot_r1"] = 2 * df["pivot"] - df["low"].shift(1)
    df["pivot_s1"] = 2 * df["pivot"] - df["high"].shift(1)
    df["pivot_r2"] = df["pivot"] + (df["high"].shift(1) - df["low"].shift(1))
    df["pivot_s2"] = df["pivot"] - (df["high"].shift(1) - df["low"].shift(1))
    return df


def _compute_keltner_channels(
    df: pd.DataFrame, ema_period: int = 20, atr_period: int = 14, multiplier: float = 1.5
) -> pd.DataFrame:
    df["keltner_mid"] = df["close"].ewm(span=ema_period, adjust=False).mean()
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    keltner_atr = tr.rolling(window=atr_period).mean()
    df["keltner_upper"] = df["keltner_mid"] + multiplier * keltner_atr
    df["keltner_lower"] = df["keltner_mid"] - multiplier * keltner_atr
    return df


def _compute_chaikin_money_flow(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (df["high"] - df["low"])
    mfm = mfm.fillna(0)
    mf_volume = mfm * df["volume"]
    df["cmf"] = mf_volume.rolling(window=period).sum() / df["volume"].rolling(window=period).sum()
    return df


# ═══════════════════════════════════════════════════════════════
# ANALYSIS FORMATTERS (existing interface preserved)
# ═══════════════════════════════════════════════════════════════

def get_volume_trend(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Analyze volume trend: rising/falling, spike detection."""
    recent = df["volume"].tail(lookback)
    avg_vol = recent.mean()
    latest_vol = df["volume"].iloc[-1]

    vol_ma5 = df["volume"].tail(5).mean()
    vol_ma20 = avg_vol

    if vol_ma5 > vol_ma20 * 1.2:
        trend = "Rising Volume 📊 (Momentum building)"
    elif vol_ma5 < vol_ma20 * 0.8:
        trend = "Declining Volume 📉 (Weak momentum)"
    else:
        trend = "Average Volume ➡️ (Neutral)"

    is_spike = latest_vol > avg_vol * 2.0
    spike_note = f"⚡ Volume Spike! ({latest_vol/avg_vol:.1f}x avg)" if is_spike else "No spike"

    latest_body = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    avg_body = df["close"].tail(20).sub(df["open"].tail(20)).abs().mean()
    is_climax = is_spike and latest_body > avg_body * 1.5

    return {
        "trend": trend,
        "spike": spike_note,
        "latest_volume": round(latest_vol, 2),
        "avg_volume_20": round(avg_vol, 2),
        "volume_ratio": round(latest_vol / avg_vol, 2) if avg_vol > 0 else 1.0,
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

    return {
        "value": rsi_val,
        "zone": zone,
        "direction": direction,
        "divergence": "None detected",
    }


def get_macd_analysis(macd: pd.Series, signal: pd.Series, hist: pd.Series) -> dict:
    macd_val = round(macd.iloc[-1], 6)
    signal_val = round(signal.iloc[-1], 6)
    hist_val = round(hist.iloc[-1], 6)
    prev_hist = round(hist.iloc[-2], 6)

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
    """Stochastic Oscillator."""
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

    if k_val >= STOCH_OVERBOUGHT:
        zone = "Overbought 🔴"
    elif k_val <= STOCH_OVERSOLD:
        zone = "Oversold 🟢"
    else:
        zone = "Neutral"

    cross = "None"
    if k_val > d_val and prev_k <= prev_d:
        cross = "🟢 Bullish Crossover (%K above %D)"
    elif k_val < d_val and prev_k >= prev_d:
        cross = "🔴 Bearish Crossover (%K below %D)"

    return {"k": k_val, "d": d_val, "zone": zone, "cross": cross}


def get_extended_indicators(df: pd.DataFrame) -> dict:
    """Get values for all new indicators (Ichimoku, Supertrend, etc.)."""
    enriched = compute_all_indicators(df)
    result = {}

    # Ichimoku
    try:
        tenkan = enriched["ichimoku_tenkan"].iloc[-1]
        kijun = enriched["ichimoku_kijun"].iloc[-1]
        price = enriched["close"].iloc[-1]
        if not pd.isna(tenkan) and not pd.isna(kijun):
            if price > tenkan > kijun:
                ichi_signal = "🟢 Bullish (Price > Tenkan > Kijun)"
            elif price < tenkan < kijun:
                ichi_signal = "🔴 Bearish (Price < Tenkan < Kijun)"
            elif tenkan > kijun:
                ichi_signal = "📗 Mild Bullish"
            else:
                ichi_signal = "📕 Mild Bearish"
        else:
            ichi_signal = "N/A"
        result["ichimoku"] = {"signal": ichi_signal, "tenkan": round(tenkan, 6) if not pd.isna(tenkan) else 0, "kijun": round(kijun, 6) if not pd.isna(kijun) else 0}
    except Exception:
        result["ichimoku"] = {"signal": "N/A", "tenkan": 0, "kijun": 0}

    # Supertrend
    try:
        st_dir = enriched["supertrend_direction"].iloc[-1]
        st_val = enriched["supertrend"].iloc[-1]
        result["supertrend"] = {
            "direction": "Bullish 🟢" if st_dir == 1 else "Bearish 🔴",
            "value": round(st_val, 6) if not pd.isna(st_val) else 0,
        }
    except Exception:
        result["supertrend"] = {"direction": "N/A", "value": 0}

    # CCI
    try:
        cci_val = enriched["cci"].iloc[-1]
        if not pd.isna(cci_val):
            if cci_val > 100:
                cci_zone = "Overbought 🔴"
            elif cci_val < -100:
                cci_zone = "Oversold 🟢"
            else:
                cci_zone = "Neutral"
            result["cci"] = {"value": round(cci_val, 1), "zone": cci_zone}
        else:
            result["cci"] = {"value": 0, "zone": "N/A"}
    except Exception:
        result["cci"] = {"value": 0, "zone": "N/A"}

    # Williams %R
    try:
        wr_val = enriched["williams_r"].iloc[-1]
        if not pd.isna(wr_val):
            if wr_val > -20:
                wr_zone = "Overbought 🔴"
            elif wr_val < -80:
                wr_zone = "Oversold 🟢"
            else:
                wr_zone = "Neutral"
            result["williams_r"] = {"value": round(wr_val, 1), "zone": wr_zone}
        else:
            result["williams_r"] = {"value": 0, "zone": "N/A"}
    except Exception:
        result["williams_r"] = {"value": 0, "zone": "N/A"}

    # MFI
    try:
        mfi_val = enriched["mfi"].iloc[-1]
        if not pd.isna(mfi_val):
            if mfi_val > 80:
                mfi_zone = "Overbought 🔴"
            elif mfi_val < 20:
                mfi_zone = "Oversold 🟢"
            else:
                mfi_zone = "Neutral"
            result["mfi"] = {"value": round(mfi_val, 1), "zone": mfi_zone}
        else:
            result["mfi"] = {"value": 0, "zone": "N/A"}
    except Exception:
        result["mfi"] = {"value": 0, "zone": "N/A"}

    # CMF
    try:
        cmf_val = enriched["cmf"].iloc[-1]
        if not pd.isna(cmf_val):
            if cmf_val > 0.05:
                cmf_label = "Buying Pressure 🟢"
            elif cmf_val < -0.05:
                cmf_label = "Selling Pressure 🔴"
            else:
                cmf_label = "Neutral"
            result["cmf"] = {"value": round(cmf_val, 3), "label": cmf_label}
        else:
            result["cmf"] = {"value": 0, "label": "N/A"}
    except Exception:
        result["cmf"] = {"value": 0, "label": "N/A"}

    # VWAP
    try:
        vwap_val = enriched["vwap"].iloc[-1]
        price = enriched["close"].iloc[-1]
        if not pd.isna(vwap_val):
            pos = "Above VWAP 🟢" if price > vwap_val else "Below VWAP 🔴"
            result["vwap"] = {"value": round(vwap_val, 6), "position": pos}
        else:
            result["vwap"] = {"value": 0, "position": "N/A"}
    except Exception:
        result["vwap"] = {"value": 0, "position": "N/A"}

    # OBV
    try:
        obv_val = enriched["obv"].iloc[-1]
        obv_sma = enriched["obv_sma"].iloc[-1]
        if not pd.isna(obv_val) and not pd.isna(obv_sma):
            obv_trend = "Rising 🟢" if obv_val > obv_sma else "Falling 🔴"
        else:
            obv_trend = "N/A"
        result["obv"] = {"trend": obv_trend}
    except Exception:
        result["obv"] = {"trend": "N/A"}

    return result, enriched


def run_indicators(df: pd.DataFrame) -> dict:
    """Run all indicators and return compiled results (backwards-compatible)."""
    rsi = calculate_rsi(df["close"])
    macd_line, signal_line, histogram = calculate_macd(df["close"])
    emas = calculate_emas(df["close"])

    result = {
        "rsi": get_rsi_analysis(rsi),
        "macd": get_macd_analysis(macd_line, signal_line, histogram),
        "ema": get_ema_analysis(df, emas),
        "volume": get_volume_trend(df),
        "stochastic": calculate_stochastic(df),
    }

    # Add extended indicators
    try:
        extended, _ = get_extended_indicators(df)
        result["extended"] = extended
    except Exception:
        result["extended"] = {}

    return result
