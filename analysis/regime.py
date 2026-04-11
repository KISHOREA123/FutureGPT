"""
Market Regime Classifier
Determines the current market regime using ADX, ATR ratio, and BB bandwidth.
Regime determines optimal strategy type and parameter adjustments.

Regimes:
  TRENDING_UP   — Clear uptrend, trade breakouts / pullbacks
  TRENDING_DOWN — Clear downtrend, trade breakdowns / rallies
  RANGING       — Sideways chop, trade S/R bounces
  VOLATILE      — High volatility, widen stops, reduce size
  QUIET         — Low volatility / compression, watch for breakout
"""


def classify_regime(
    adx_val: float,
    adx_rising: bool,
    ema_bias: str,
    atr_ratio: float,
    bb_squeeze_ratio: float,
    trend_label: str,
) -> dict:
    """
    Classify market regime from pre-computed analysis data.

    Args:
        adx_val:          ADX value (0-100)
        adx_rising:       Whether ADX is increasing
        ema_bias:         "bullish" / "bearish" / "mixed"
        atr_ratio:        Current ATR / 50-candle avg ATR
        bb_squeeze_ratio: Current BB bandwidth / avg bandwidth
        trend_label:      Trend label from market structure
    """

    # ── Step 1: Detect compression / quiet ────────────
    if bb_squeeze_ratio < 0.5 and adx_val < 20:
        regime = "QUIET"
        label = "😴 QUIET — Compression detected"
        advice = "Watch for breakout. Place alerts at BB bands. Don't force trades."
        color = "⚪"

    # ── Step 2: Detect high volatility ────────────────
    elif atr_ratio > 1.5 and adx_val < 20:
        regime = "VOLATILE"
        label = "🔥 VOLATILE — Erratic price action"
        advice = "Widen stops by 1.5x. Reduce position size. Avoid choppy zones."
        color = "🟠"

    # ── Step 3: Detect trending ───────────────────────
    elif adx_val >= 25:
        if ema_bias == "bullish" or "Uptrend" in trend_label:
            regime = "TRENDING_UP"
            label = "🚀 TRENDING UP — Strong bullish momentum"
            advice = "Trade pullbacks to EMA21. Trail stops. Avoid shorts."
            color = "🟢"
        elif ema_bias == "bearish" or "Downtrend" in trend_label:
            regime = "TRENDING_DOWN"
            label = "💥 TRENDING DOWN — Strong bearish momentum"
            advice = "Trade rallies to EMA21. Trail stops. Avoid longs."
            color = "🔴"
        else:
            regime = "TRENDING_UP" if adx_rising else "RANGING"
            label = "📈 TRENDING — Direction developing" if adx_rising else "↔️ RANGING"
            advice = "Wait for directional confirmation." if adx_rising else "Trade S/R bounces."
            color = "🟡"

    # ── Step 4: Ranging ───────────────────────────────
    else:
        regime = "RANGING"
        label = "↔️ RANGING — Sideways market"
        advice = "Trade S/R bounces. Use tight stops. Avoid breakout plays."
        color = "🟡"

    # Strategy suggestion based on regime
    strategies = {
        "TRENDING_UP": "Trend Following — Buy dips to EMA21/55, trail SL below swing lows",
        "TRENDING_DOWN": "Trend Following — Sell rallies to EMA21/55, trail SL above swing highs",
        "RANGING": "Mean Reversion — Buy at support, sell at resistance, tight SL",
        "VOLATILE": "Scalp / Hedge — Small size, wide SL, quick TP at nearest level",
        "QUIET": "Breakout Watch — Set alerts at key levels, wait for expansion",
    }

    return {
        "regime": regime,
        "label": label,
        "color": color,
        "advice": advice,
        "strategy": strategies.get(regime, ""),
        "components": {
            "adx": adx_val,
            "adx_rising": adx_rising,
            "atr_ratio": atr_ratio,
            "bb_squeeze_ratio": bb_squeeze_ratio,
        },
    }
