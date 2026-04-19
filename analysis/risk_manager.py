"""
Risk Manager — Enhanced v2.0
Position Sizing, SL/TP, R:R Calculation + Kelly Criterion,
Volatility-Adjusted Sizing, and Drawdown Circuit Breaker.
"""
import math
from config import (
    DEFAULT_RISK_PCT, DEFAULT_ACCOUNT_SIZE, MAX_LEVERAGE,
    MIN_RR_RATIO, TP1_MULTIPLIER, TP2_MULTIPLIER, ATR_SL_MULTIPLIER,
    DEFAULT_CAPITAL, MAX_DRAWDOWN_PERCENT, DEFAULT_RISK_PER_TRADE,
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
    """
    if atr_value <= 0 or current_price <= 0:
        return {"error": "Invalid ATR or price"}

    sl_multiplier = ATR_SL_MULTIPLIER

    # Adjust SL distance based on volatility
    if "High" in atr_regime:
        sl_multiplier = 2.0
    elif "Low" in atr_regime:
        sl_multiplier = 1.0

    sl_distance = atr_value * sl_multiplier

    # ── SL placement with S/R snapping ───────────────
    if signal_direction == "BUY":
        raw_sl = current_price - sl_distance
        if nearest_support:
            sr_level = nearest_support["level"]
            sr_sl = sr_level - (atr_value * 0.3)
            if abs(current_price - sr_sl) <= atr_value * 2:
                raw_sl = min(raw_sl, sr_sl)

        sl_price = raw_sl
        tp1_price = current_price + (sl_distance * TP1_MULTIPLIER)
        tp2_price = current_price + (sl_distance * TP2_MULTIPLIER)
        tp3_price = current_price + (sl_distance * 3.5)  # TP3 = 3.5x risk

        if nearest_resistance:
            r_level = nearest_resistance["level"]
            if abs(tp1_price - r_level) / current_price < 0.02:
                tp1_price = r_level * 0.998

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
        tp3_price = current_price - (sl_distance * 3.5)

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
        "tp3": fmt(tp3_price),
        "tp3_raw": tp3_price,
        "sl_distance_pct": round(risk_distance / current_price * 100, 2),
        "rr_ratio": rr_ratio,
        "rr_ratio_tp2": round(abs(tp2_price - current_price) / risk_distance, 2) if risk_distance > 0 else 0,
        "rr_ratio_tp3": round(abs(tp3_price - current_price) / risk_distance, 2) if risk_distance > 0 else 0,
        "rr_verdict": rr_verdict,
        "risk_amount": round(risk_amount, 2),
        "position_size_usd": round(position_size_usd, 2),
        "position_size_units": round(position_size_units, 6),
        "leverage": suggested_leverage,
        "tradeable": tradeable,
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Advanced Risk Management Methods
# ═══════════════════════════════════════════════════════════════

def kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
) -> dict:
    """
    Kelly Criterion — Optimal position sizing based on historical performance.

    Args:
        win_rate: Historical win rate (0-1)
        avg_win: Average winning trade profit (absolute)
        avg_loss: Average losing trade loss (absolute)

    Returns:
        dict with kelly fraction, recommended risk %, and assessment
    """
    if avg_loss <= 0 or avg_win <= 0 or win_rate <= 0 or win_rate >= 1:
        return {
            "kelly_fraction": 0,
            "recommended_risk_pct": DEFAULT_RISK_PER_TRADE,
            "assessment": "⚠️ Insufficient data for Kelly Criterion",
        }

    win_loss_ratio = avg_win / avg_loss
    kelly_f = win_rate - ((1 - win_rate) / win_loss_ratio)

    # Half-Kelly for safety (fractional Kelly)
    half_kelly = max(0, kelly_f * 0.5)
    recommended_pct = round(min(half_kelly * 100, 5.0), 2)  # Cap at 5%

    if kelly_f > 0.25:
        assessment = "🟢 Strong edge — Kelly suggests aggressive sizing"
    elif kelly_f > 0.10:
        assessment = "📗 Moderate edge — Use fractional Kelly"
    elif kelly_f > 0:
        assessment = "⚠️ Slim edge — Use conservative sizing"
    else:
        assessment = "🔴 Negative edge — Do NOT trade this strategy"

    return {
        "kelly_fraction": round(kelly_f, 4),
        "half_kelly": round(half_kelly, 4),
        "recommended_risk_pct": recommended_pct,
        "assessment": assessment,
        "win_rate": round(win_rate * 100, 1),
        "win_loss_ratio": round(win_loss_ratio, 2),
    }


def volatility_adjusted_size(
    capital: float,
    atr_value: float,
    current_price: float,
    base_risk_pct: float = DEFAULT_RISK_PER_TRADE,
    target_atr_pct: float = 2.0,
) -> dict:
    """
    Adjust position size based on current volatility (ATR).
    Higher volatility → smaller position. Lower volatility → larger position.

    Args:
        capital: Account capital
        atr_value: Current ATR value
        current_price: Current price
        base_risk_pct: Base risk percentage
        target_atr_pct: Target ATR% for normal conditions
    """
    if current_price <= 0 or atr_value <= 0:
        return {"position_size_usd": 0, "adjustment": "N/A"}

    atr_pct = (atr_value / current_price) * 100
    vol_ratio = target_atr_pct / atr_pct if atr_pct > 0 else 1.0

    # Clamp adjustment between 0.3x and 2.0x
    vol_ratio = max(0.3, min(2.0, vol_ratio))

    adjusted_risk_pct = base_risk_pct * vol_ratio
    risk_amount = capital * (adjusted_risk_pct / 100)
    position_size = risk_amount / (atr_value * ATR_SL_MULTIPLIER) * current_price

    if vol_ratio < 0.6:
        label = "🔴 High volatility — Position reduced"
    elif vol_ratio < 0.9:
        label = "🟠 Above-average volatility — Slightly reduced"
    elif vol_ratio < 1.2:
        label = "🟢 Normal volatility — Standard sizing"
    else:
        label = "🔵 Low volatility — Position increased"

    return {
        "position_size_usd": round(position_size, 2),
        "adjusted_risk_pct": round(adjusted_risk_pct, 2),
        "volatility_ratio": round(vol_ratio, 2),
        "atr_pct": round(atr_pct, 2),
        "adjustment": label,
    }


def max_drawdown_guard(
    current_drawdown_pct: float,
    max_drawdown_pct: float = MAX_DRAWDOWN_PERCENT,
    consecutive_losses: int = 0,
) -> dict:
    """
    Circuit breaker — reduces or halts trading based on drawdown.

    Args:
        current_drawdown_pct: Current portfolio drawdown percentage
        max_drawdown_pct: Maximum allowable drawdown before halt
        consecutive_losses: Number of consecutive losing trades
    """
    if current_drawdown_pct >= max_drawdown_pct:
        return {
            "action": "HALT",
            "label": "🛑 CIRCUIT BREAKER — Max drawdown reached. STOP TRADING.",
            "reduce_size": 0,
            "risk_level": "critical",
        }

    if current_drawdown_pct >= max_drawdown_pct * 0.75:
        return {
            "action": "REDUCE",
            "label": f"🔴 DANGER — Drawdown at {current_drawdown_pct:.1f}%. Reduce size by 75%.",
            "reduce_size": 0.25,
            "risk_level": "danger",
        }

    if current_drawdown_pct >= max_drawdown_pct * 0.50:
        return {
            "action": "CAUTION",
            "label": f"🟠 CAUTION — Drawdown at {current_drawdown_pct:.1f}%. Reduce size by 50%.",
            "reduce_size": 0.50,
            "risk_level": "caution",
        }

    if consecutive_losses >= 5:
        return {
            "action": "COOL_DOWN",
            "label": f"⚠️ {consecutive_losses} consecutive losses. Take a break.",
            "reduce_size": 0.50,
            "risk_level": "warning",
        }

    if consecutive_losses >= 3:
        return {
            "action": "REDUCE",
            "label": f"⚠️ {consecutive_losses} consecutive losses. Reduce position size.",
            "reduce_size": 0.75,
            "risk_level": "mild",
        }

    return {
        "action": "NORMAL",
        "label": "🟢 Normal — All risk controls within limits.",
        "reduce_size": 1.0,
        "risk_level": "normal",
    }


def calculate_risk_metrics(
    entry_price: float,
    sl_price: float,
    tp1_price: float,
    tp2_price: float,
    tp3_price: float,
    atr_value: float,
    capital: float = DEFAULT_CAPITAL,
) -> dict:
    """
    Calculate comprehensive risk metrics for a trade setup.
    """
    if entry_price <= 0 or sl_price <= 0 or atr_value <= 0:
        return {}

    risk_distance = abs(entry_price - sl_price)
    atr_risk = risk_distance / atr_value if atr_value > 0 else 0

    def rr(tp):
        return round(abs(tp - entry_price) / risk_distance, 2) if risk_distance > 0 else 0

    rr1 = rr(tp1_price)
    rr2 = rr(tp2_price)
    rr3 = rr(tp3_price)

    # Breakeven win rate
    breakeven_wr = round(1 / (1 + rr1) * 100, 1) if rr1 > 0 else 100

    # Risk per trade in USD
    risk_pct = DEFAULT_RISK_PER_TRADE
    risk_usd = capital * (risk_pct / 100)

    return {
        "risk_distance": round(risk_distance, 6),
        "risk_pct_of_price": round(risk_distance / entry_price * 100, 2),
        "atr_risk_multiple": round(atr_risk, 2),
        "rr_tp1": rr1,
        "rr_tp2": rr2,
        "rr_tp3": rr3,
        "breakeven_winrate": breakeven_wr,
        "risk_usd": round(risk_usd, 2),
        "potential_profit_tp1": round(risk_usd * rr1, 2),
        "potential_profit_tp2": round(risk_usd * rr2, 2),
        "potential_profit_tp3": round(risk_usd * rr3, 2),
    }
