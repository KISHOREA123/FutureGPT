import pandas as pd
import numpy as np


def find_local_extremes(series: pd.Series, order: int = 5) -> tuple[list, list]:
    """Find local highs and lows in a series."""
    highs, lows = [], []
    for i in range(order, len(series) - order):
        window = series.iloc[i - order: i + order + 1]
        if series.iloc[i] == window.max():
            highs.append(i)
        if series.iloc[i] == window.min():
            lows.append(i)
    return highs, lows


def detect_rsi_divergence(df: pd.DataFrame, rsi: pd.Series, order: int = 5) -> dict:
    """
    Detect Regular and Hidden RSI divergence.
    
    Regular Bullish:  Price makes Lower Low, RSI makes Higher Low → Bullish reversal signal
    Regular Bearish:  Price makes Higher High, RSI makes Lower High → Bearish reversal signal
    Hidden Bullish:   Price makes Higher Low, RSI makes Lower Low → Trend continuation up
    Hidden Bearish:   Price makes Lower High, RSI makes Higher High → Trend continuation down
    """
    price = df["close"]
    price_highs, price_lows = find_local_extremes(price, order)
    rsi_highs, rsi_lows = find_local_extremes(rsi, order)

    divergences = []

    # Regular Bullish: price LL, RSI HL
    if len(price_lows) >= 2 and len(rsi_lows) >= 2:
        p1, p2 = price_lows[-2], price_lows[-1]
        r1, r2 = rsi_lows[-2], rsi_lows[-1]
        if price.iloc[p2] < price.iloc[p1] and rsi.iloc[r2] > rsi.iloc[r1]:
            divergences.append({
                "type": "🟢 Regular Bullish Divergence",
                "signal": "Potential reversal UP",
                "strength": "Strong",
                "indicator": "RSI",
            })

    # Regular Bearish: price HH, RSI LH
    if len(price_highs) >= 2 and len(rsi_highs) >= 2:
        p1, p2 = price_highs[-2], price_highs[-1]
        r1, r2 = rsi_highs[-2], rsi_highs[-1]
        if price.iloc[p2] > price.iloc[p1] and rsi.iloc[r2] < rsi.iloc[r1]:
            divergences.append({
                "type": "🔴 Regular Bearish Divergence",
                "signal": "Potential reversal DOWN",
                "strength": "Strong",
                "indicator": "RSI",
            })

    # Hidden Bullish: price HL, RSI LL
    if len(price_lows) >= 2 and len(rsi_lows) >= 2:
        p1, p2 = price_lows[-2], price_lows[-1]
        r1, r2 = rsi_lows[-2], rsi_lows[-1]
        if price.iloc[p2] > price.iloc[p1] and rsi.iloc[r2] < rsi.iloc[r1]:
            divergences.append({
                "type": "🔵 Hidden Bullish Divergence",
                "signal": "Uptrend continuation likely",
                "strength": "Moderate",
                "indicator": "RSI",
            })

    # Hidden Bearish: price LH, RSI HH
    if len(price_highs) >= 2 and len(rsi_highs) >= 2:
        p1, p2 = price_highs[-2], price_highs[-1]
        r1, r2 = rsi_highs[-2], rsi_highs[-1]
        if price.iloc[p2] < price.iloc[p1] and rsi.iloc[r2] > rsi.iloc[r1]:
            divergences.append({
                "type": "🟠 Hidden Bearish Divergence",
                "signal": "Downtrend continuation likely",
                "strength": "Moderate",
                "indicator": "RSI",
            })

    return {
        "divergences": divergences,
        "count": len(divergences),
        "summary": divergences[0]["type"] if divergences else "No divergence detected",
    }


def detect_macd_divergence(df: pd.DataFrame, macd_line: pd.Series, order: int = 5) -> dict:
    """Detect divergence between price and MACD line."""
    price = df["close"]
    price_highs, price_lows = find_local_extremes(price, order)
    macd_highs, macd_lows = find_local_extremes(macd_line, order)

    divergences = []

    # Regular Bullish
    if len(price_lows) >= 2 and len(macd_lows) >= 2:
        p1, p2 = price_lows[-2], price_lows[-1]
        m1, m2 = macd_lows[-2], macd_lows[-1]
        if price.iloc[p2] < price.iloc[p1] and macd_line.iloc[m2] > macd_line.iloc[m1]:
            divergences.append({
                "type": "🟢 Regular Bullish Divergence",
                "signal": "Potential reversal UP",
                "indicator": "MACD",
            })

    # Regular Bearish
    if len(price_highs) >= 2 and len(macd_highs) >= 2:
        p1, p2 = price_highs[-2], price_highs[-1]
        m1, m2 = macd_highs[-2], macd_highs[-1]
        if price.iloc[p2] > price.iloc[p1] and macd_line.iloc[m2] < macd_line.iloc[m1]:
            divergences.append({
                "type": "🔴 Regular Bearish Divergence",
                "signal": "Potential reversal DOWN",
                "indicator": "MACD",
            })

    return {
        "divergences": divergences,
        "count": len(divergences),
        "summary": divergences[0]["type"] if divergences else "No divergence detected",
    }
