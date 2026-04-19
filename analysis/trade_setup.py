"""
Trade Setup Generator — Complete Actionable Trade Card
Combines all analysis modules into a single trade verdict with entry/SL/TP.
Applies a quality gate to filter noise.
"""
from config import (
    MIN_CONFLUENCE_SCORE, MIN_GRADE_TRADEABLE, MIN_CONFIDENCE_PCT,
    VOLUME_CONFIRMATION,
)
from analysis.risk_manager import calculate_position
from analysis.signal_grader import compute_confidence


# Grade ranking for comparison
GRADE_RANK = {
    "A+": 8, "A": 7, "B+": 6, "B": 5,
    "C+": 4, "C": 3, "D": 2, "F": 1,
}


def generate_trade_setup(
    symbol: str,
    timeframe: str,
    current_price: float,
    confluence: dict,
    indicators: dict,
    patterns: list,
    div_rsi: dict,
    div_macd: dict,
    trend_data: dict,
    regime_data: dict,
    atr_data: dict,
    ob_data: dict,
    fvg_data: dict,
    sr_data: dict,
    htf_bias: dict = None,
    harmonic_data: dict = None,
    order_flow_data: dict = None,
    ml_data: dict = None,
    session_data: dict = None,
) -> dict:
    """
    Generate a complete trade setup or WAIT/AVOID verdict.
    This is the final quality gate — only actionable setups pass.
    """
    score = confluence.get("score", 0)
    bias = confluence.get("bias", "NEUTRAL")
    abs_score = abs(score)

    # ── Step 1: Determine direction ──────────────────
    if score >= MIN_CONFLUENCE_SCORE:
        direction = "BUY"
    elif score <= -MIN_CONFLUENCE_SCORE:
        direction = "SELL"
    else:
        return _no_trade(symbol, timeframe, current_price, score, bias,
                         reason="Confluence too weak for a trade setup")

    # ── Step 2: Compute signal grade ─────────────────
    grade_data = compute_confidence(
        confluence_score=score,
        volume_data=indicators.get("volume", {}),
        patterns=patterns,
        div_rsi=div_rsi,
        div_macd=div_macd,
        trend_data=trend_data,
        ob_data=ob_data,
        fvg_data=fvg_data,
        regime_data=regime_data,
        htf_bias=htf_bias,
        confluence_bias=bias,
        harmonic_data=harmonic_data,
        order_flow_data=order_flow_data,
        ml_data=ml_data,
        session_data=session_data,
    )

    grade = grade_data["grade"]
    confidence = grade_data["confidence_pct"]

    # ── Step 3: Quality gate checks ──────────────────
    fail_reasons = []

    # Grade check
    min_rank = GRADE_RANK.get(MIN_GRADE_TRADEABLE, 4)
    actual_rank = GRADE_RANK.get(grade, 0)
    if actual_rank < min_rank:
        fail_reasons.append(f"Grade {grade} below minimum {MIN_GRADE_TRADEABLE}")

    # Confidence check
    if confidence < MIN_CONFIDENCE_PCT:
        fail_reasons.append(f"Confidence {confidence}% below minimum {MIN_CONFIDENCE_PCT}%")

    # Volume check
    if VOLUME_CONFIRMATION:
        vol_trend = indicators.get("volume", {}).get("trend", "")
        if "Declining" in vol_trend:
            fail_reasons.append("Declining volume — no confirmation")

    # Regime check (counter-trend penalty)
    regime = regime_data.get("regime", "")
    if regime == "TRENDING_UP" and direction == "SELL":
        fail_reasons.append("Bearish signal in strong uptrend (counter-trend)")
    elif regime == "TRENDING_DOWN" and direction == "BUY":
        fail_reasons.append("Bullish signal in strong downtrend (counter-trend)")

    # ── Step 4: Generate risk-managed position ───────
    atr_val = atr_data.get("atr", 0)
    volatility_label = atr_data.get("volatility", "Normal")

    position = calculate_position(
        current_price=current_price,
        atr_value=atr_val,
        signal_direction=direction,
        nearest_support=sr_data.get("nearest_support"),
        nearest_resistance=sr_data.get("nearest_resistance"),
        atr_regime=volatility_label,
    )

    # R:R gate
    if position.get("rr_ratio", 0) < 1.5:
        fail_reasons.append(f"R:R ratio {position.get('rr_ratio', 0)} below 1.5x minimum")

    # ── Step 5: Final verdict ────────────────────────
    if fail_reasons:
        verdict = "⏳ WAIT"
        verdict_detail = "Signal detected but quality gate not passed"
        tradeable = False
    else:
        if confidence >= 70 and grade in ("A+", "A", "B+"):
            verdict = "🟢 TRADE — High Confidence"
            verdict_detail = "All quality checks passed. Strong setup."
        elif confidence >= 50:
            verdict = "🟡 TRADE — Moderate Confidence"
            verdict_detail = "Quality checks passed. Acceptable setup."
        else:
            verdict = "🟡 TRADE — Low Confidence"
            verdict_detail = "Minimum requirements met. Proceed with caution."
        tradeable = True

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price": current_price,
        "direction": direction,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "tradeable": tradeable,
        "confluence_score": score,
        "confluence_bias": bias,
        "grade": grade_data,
        "position": position,
        "regime": regime_data,
        "fail_reasons": fail_reasons,
        "quality_checks": {
            "confluence_pass": abs_score >= MIN_CONFLUENCE_SCORE,
            "grade_pass": actual_rank >= min_rank,
            "confidence_pass": confidence >= MIN_CONFIDENCE_PCT,
            "rr_pass": position.get("rr_ratio", 0) >= 1.5,
            "volume_pass": "Declining" not in indicators.get("volume", {}).get("trend", ""),
            "regime_pass": not (
                (regime == "TRENDING_UP" and direction == "SELL") or
                (regime == "TRENDING_DOWN" and direction == "BUY")
            ),
        },
    }


def _no_trade(symbol, tf, price, score, bias, reason):
    """Return a structured no-trade response."""
    return {
        "symbol": symbol,
        "timeframe": tf,
        "current_price": price,
        "direction": "NEUTRAL",
        "verdict": "🔴 AVOID",
        "verdict_detail": reason,
        "tradeable": False,
        "confluence_score": score,
        "confluence_bias": bias,
        "grade": {"confidence_pct": 0, "grade": "F", "factors": [], "factor_count": 0, "warning_count": 0},
        "position": {},
        "regime": {},
        "fail_reasons": [reason],
        "quality_checks": {},
    }
