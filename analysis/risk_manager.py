"""
Risk Manager — Position Sizing, SL/TP, R:R Calculation
Generates complete risk-managed trade parameters.
"""
from config import (
    DEFAULT_RISK_PCT, DEFAULT_ACCOUNT_SIZE, MAX_LEVERAGE,
    MIN_RR_RATIO, TP1_MULTIPLIER, TP2_MULTIPLIER, ATR_SL_MULTIPLIER,
)


def calculate_position(
    current_price: float,
    atr_value: float,
    signal_direction: str,
    nearest_support: dict = None,
    nearest_resistance: dict = None,
    account_size: float = DEFAULT_ACCOUNT_SIZE,
    risk_pct: float = DEFAULT_RISK_PCT,
    atr_regime: str = "Normal",
) -> dict:
    """
    Calculate complete position sizing with SL/TP levels.

    Args:
        current_price:     Current market price
        atr_value:         Current ATR value
        signal_direction:  "BUY" or "SELL"
        nearest_support:   Dict with 'level' key (nearest support price)
        nearest_resistance: Dict with 'level' key (nearest resistance price)
        account_size:      Trading account size in USD
        risk_pct:          Risk percentage per trade
        atr_regime:        Volatility label for leverage adjustment
    """
    if atr_value <= 0 or current_price <= 0:
        return {"error": "Invalid ATR or price"}

    sl_multiplier = ATR_SL_MULTIPLIER

    # Adjust SL distance based on volatility
    if "High" in atr_regime:
        sl_multiplier = 2.0  # Wider SL in volatile markets
    elif "Low" in atr_regime:
        sl_multiplier = 1.0  # Tighter SL in quiet markets

    sl_distance = atr_value * sl_multiplier

    # ── SL placement with S/R snapping ───────────────
    if signal_direction == "BUY":
        raw_sl = current_price - sl_distance
        # Snap SL below nearest support if it's close
        if nearest_support:
            sr_level = nearest_support["level"]
            sr_sl = sr_level - (atr_value * 0.3)  # Place SL just below support
            # Use S/R-snapped SL if it's within 2x ATR of price
            if abs(current_price - sr_sl) <= atr_value * 2:
                raw_sl = min(raw_sl, sr_sl)  # Use whichever is tighter

        sl_price = raw_sl
        tp1_price = current_price + (sl_distance * TP1_MULTIPLIER)
        tp2_price = current_price + (sl_distance * TP2_MULTIPLIER)

        # Snap TP to resistance if close
        if nearest_resistance:
            r_level = nearest_resistance["level"]
            if abs(tp1_price - r_level) / current_price < 0.02:
                tp1_price = r_level * 0.998  # Just below resistance

    elif signal_direction == "SELL":
        raw_sl = current_price + sl_distance
        if nearest_resistance:
            sr_level = nearest_resistance["level"]
            sr_sl = sr_level + (atr_value * 0.3)
            if abs(sr_sl - current_price) <= atr_value * 2:
                raw_sl = max(raw_sl, sr_sl)

        sl_price = raw_sl
        tp1_price = current_price - (sl_distance * TP1_MULTIPLIER)
        tp2_price = current_price - (sl_distance * TP2_MULTIPLIER)

        if nearest_support:
            s_level = nearest_support["level"]
            if abs(tp1_price - s_level) / current_price < 0.02:
                tp1_price = s_level * 1.002
    else:
        return {"error": "No clear signal direction", "tradeable": False}

    # ── Risk:Reward ratio ────────────────────────────
    risk_distance = abs(current_price - sl_price)
    reward_distance = abs(tp1_price - current_price)
    rr_ratio = round(reward_distance / risk_distance, 2) if risk_distance > 0 else 0

    # ── Position sizing ──────────────────────────────
    risk_amount = account_size * (risk_pct / 100)
    risk_per_unit = risk_distance
    position_size_units = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
    position_size_usd = position_size_units * current_price

    # ── Leverage suggestion ──────────────────────────
    raw_leverage = position_size_usd / account_size if account_size > 0 else 1
    suggested_leverage = max(1, min(int(raw_leverage), MAX_LEVERAGE))

    # Reduce leverage in volatile regimes
    if "High" in atr_regime:
        suggested_leverage = max(1, suggested_leverage // 2)

    # ── Tradeable check ──────────────────────────────
    tradeable = rr_ratio >= MIN_RR_RATIO
    rr_verdict = "✅ Favorable" if rr_ratio >= 2.0 else (
        "⚠️ Acceptable" if rr_ratio >= MIN_RR_RATIO else "❌ Poor R:R"
    )

    def fmt(v):
        if current_price >= 1000:
            return f"${v:,.2f}"
        elif current_price >= 1:
            return f"${v:.4f}"
        else:
            return f"${v:.6f}"

    return {
        "direction": signal_direction,
        "entry": fmt(current_price),
        "entry_raw": current_price,
        "sl": fmt(sl_price),
        "sl_raw": sl_price,
        "tp1": fmt(tp1_price),
        "tp1_raw": tp1_price,
        "tp2": fmt(tp2_price),
        "tp2_raw": tp2_price,
        "sl_distance_pct": round(risk_distance / current_price * 100, 2),
        "rr_ratio": rr_ratio,
        "rr_verdict": rr_verdict,
        "risk_amount": round(risk_amount, 2),
        "position_size_usd": round(position_size_usd, 2),
        "position_size_units": round(position_size_units, 6),
        "leverage": suggested_leverage,
        "tradeable": tradeable,
    }
