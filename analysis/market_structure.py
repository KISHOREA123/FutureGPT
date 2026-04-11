import pandas as pd
import numpy as np


def find_swing_points(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """Identify swing highs and swing lows."""
    df = df.copy()
    df["swing_high"] = False
    df["swing_low"] = False

    for i in range(lookback, len(df) - lookback):
        window_high = df["high"].iloc[i - lookback: i + lookback + 1]
        window_low = df["low"].iloc[i - lookback: i + lookback + 1]

        if df["high"].iloc[i] == window_high.max():
            df.iloc[i, df.columns.get_loc("swing_high")] = True
        if df["low"].iloc[i] == window_low.min():
            df.iloc[i, df.columns.get_loc("swing_low")] = True

    return df


def detect_market_structure(df: pd.DataFrame) -> dict:
    """
    Detect market structure: HH, HL, LH, LL pattern.
    Returns trend direction and recent swing sequence.
    """
    swing_df = find_swing_points(df)

    swing_highs = df["high"][swing_df["swing_high"]].values
    swing_lows = df["low"][swing_df["swing_low"]].values

    structure_notes = []
    trend = "Sideways"

    # Analyze last 3-4 swing highs
    if len(swing_highs) >= 2:
        if swing_highs[-1] > swing_highs[-2]:
            structure_notes.append("HH (Higher High)")
        elif swing_highs[-1] < swing_highs[-2]:
            structure_notes.append("LH (Lower High)")
        else:
            structure_notes.append("Equal High")

    # Analyze last 3-4 swing lows
    if len(swing_lows) >= 2:
        if swing_lows[-1] > swing_lows[-2]:
            structure_notes.append("HL (Higher Low)")
        elif swing_lows[-1] < swing_lows[-2]:
            structure_notes.append("LL (Lower Low)")
        else:
            structure_notes.append("Equal Low")

    # Determine overall trend
    if "HH (Higher High)" in structure_notes and "HL (Higher Low)" in structure_notes:
        trend = "Uptrend 📈"
    elif "LH (Lower High)" in structure_notes and "LL (Lower Low)" in structure_notes:
        trend = "Downtrend 📉"
    elif "HH (Higher High)" in structure_notes and "LL (Lower Low)" in structure_notes:
        trend = "Choppy / Distribution ↔️"
    elif "LH (Lower High)" in structure_notes and "HL (Higher Low)" in structure_notes:
        trend = "Choppy / Accumulation ↔️"
    else:
        trend = "Sideways ↔️"

    # Detect Break of Structure (BOS) or Change of Character (CHoCH)
    bos_choch = "None"
    recent_close = df["close"].iloc[-1]
    if len(swing_highs) >= 1 and recent_close > swing_highs[-1]:
        bos_choch = "🟢 BOS UP (Break of Structure - Bullish)"
    elif len(swing_lows) >= 1 and recent_close < swing_lows[-1]:
        bos_choch = "🔴 BOS DOWN (Break of Structure - Bearish)"

    last_high = float(swing_highs[-1]) if len(swing_highs) > 0 else None
    last_low = float(swing_lows[-1]) if len(swing_lows) > 0 else None

    return {
        "trend": trend,
        "structure_sequence": structure_notes,
        "bos_choch": bos_choch,
        "last_swing_high": last_high,
        "last_swing_low": last_low,
    }
