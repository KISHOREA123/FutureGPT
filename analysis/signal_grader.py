"""
Signal Quality Grader — Enhanced v2.0
Assigns A+ to F letter grades and confidence percentages to signals.
Now includes: harmonic pattern, order flow, ML prediction, news, session factors.

Grade Scale:
  A+ (≥90%)  A (≥80%)  B+ (≥70%)  B (≥60%)
  C+ (≥50%)  C (≥40%)  D  (≥30%)  F (<30%)
"""

# High-reliability patterns get bonus points
HIGH_RELIABILITY_PATTERNS = {
    "Bullish Engulfing", "Bearish Engulfing",
    "Morning Star", "Evening Star",
    "Three White Soldiers", "Three Black Crows",
    "Hammer", "Shooting Star",
    "Bullish Kicker", "Bearish Kicker",
    "Bullish Abandoned Baby", "Bearish Abandoned Baby",
}


def compute_confidence(
    confluence_score: int,
    volume_data: dict,
    patterns: list,
    div_rsi: dict,
    div_macd: dict,
    trend_data: dict,
    ob_data: dict,
    fvg_data: dict,
    regime_data: dict,
    htf_bias: dict = None,
    confluence_bias: str = "",
    harmonic_data: dict = None,
    order_flow_data: dict = None,
    ml_data: dict = None,
    session_data: dict = None,
) -> dict:
    """
    Compute signal confidence (0-100%) and letter grade.
    """
    factors = []
    raw_score = 0.0

    # ── 1. Confluence strength (0-25 points) ─────────
    conf_abs = abs(confluence_score)
    conf_pts = min(conf_abs / 10.0 * 25, 25)
    raw_score += conf_pts
    if conf_abs >= 7:
        factors.append(f"✅ Strong confluence ({confluence_score:+d}/10) +{conf_pts:.0f}")
    elif conf_abs >= 4:
        factors.append(f"✅ Moderate confluence ({confluence_score:+d}/10) +{conf_pts:.0f}")
    elif conf_abs >= 1:
        factors.append(f"⚠️ Weak confluence ({confluence_score:+d}/10) +{conf_pts:.0f}")
    else:
        factors.append(f"❌ No directional confluence (0/10)")

    # ── 2. Volume confirmation (0-12 points) ─────────
    vol_trend = volume_data.get("trend", "")
    vol_spike = volume_data.get("spike", "")
    vol_pts = 0
    if "Rising" in vol_trend:
        vol_pts += 7
        factors.append("✅ Rising volume confirms move +7")
    elif "Declining" in vol_trend:
        vol_pts -= 5
        factors.append("❌ Declining volume weakens signal -5")
    if "Spike" in vol_spike:
        vol_pts += 5
        factors.append("✅ Volume spike detected +5")
    raw_score += max(0, vol_pts)

    # ── 3. Candlestick patterns (0-12 points) ────────
    pat_pts = 0
    for p in patterns[:3]:
        is_hr = any(hr in p["pattern"] for hr in HIGH_RELIABILITY_PATTERNS)
        reliability = p.get("reliability", "moderate")
        if is_hr or reliability in ("high", "very_high"):
            pat_pts += 4
            factors.append(f"✅ High-reliability: {p['pattern']} +4")
        else:
            pat_pts += 2
    raw_score += min(pat_pts, 12)

    # ── 4. Divergence (0-10 points) ──────────────────
    all_divs = div_rsi.get("divergences", []) + div_macd.get("divergences", [])
    div_pts = 0
    for d in all_divs[:2]:
        if "Regular" in d["type"]:
            div_pts += 5
            factors.append(f"✅ {d['type']} (strong reversal) +5")
        elif "Hidden" in d["type"]:
            div_pts += 3
            factors.append(f"✅ {d['type']} (continuation) +3")
    raw_score += min(div_pts, 10)

    # ── 5. Trend strength / ADX (0-8 points) ────────
    adx_val = trend_data.get("adx", {}).get("adx", 0)
    if adx_val >= 30:
        raw_score += 8
        factors.append(f"✅ Strong trend (ADX {adx_val}) +8")
    elif adx_val >= 25:
        raw_score += 5
        factors.append(f"✅ Trending (ADX {adx_val}) +5")
    elif adx_val >= 15:
        raw_score += 2
        factors.append(f"⚠️ Weak trend (ADX {adx_val}) +2")
    else:
        factors.append(f"❌ No trend (ADX {adx_val})")

    # ── 6. OB/FVG proximity (0-8 points) ────────────
    smc_pts = 0
    if ob_data.get("at_ob"):
        smc_pts += 5
        factors.append(f"✅ Price at Order Block +5")
    elif ob_data.get("nearest_bull") or ob_data.get("nearest_bear"):
        smc_pts += 2
        factors.append("⚠️ Near Order Block +2")
    if fvg_data.get("at_fvg"):
        smc_pts += 3
        factors.append(f"✅ Price inside FVG +3")
    raw_score += min(smc_pts, 8)

    # ── 7. Regime suitability (0-7 points) ──────────
    regime = regime_data.get("regime", "RANGING")
    conf_direction = "bullish" if confluence_score > 0 else "bearish" if confluence_score < 0 else "neutral"

    if regime == "TRENDING_UP" and conf_direction == "bullish":
        raw_score += 7
        factors.append("✅ Bullish signal in uptrend regime +7")
    elif regime == "TRENDING_DOWN" and conf_direction == "bearish":
        raw_score += 7
        factors.append("✅ Bearish signal in downtrend regime +7")
    elif regime in ("TRENDING_UP", "TRENDING_DOWN"):
        raw_score -= 4
        factors.append("❌ Counter-trend signal: regime mismatch -4")
    elif regime == "QUIET":
        raw_score += 2
        factors.append("⚠️ Quiet regime: breakout watch +2")
    elif regime == "VOLATILE":
        raw_score -= 3
        factors.append("⚠️ Volatile regime: noise risk -3")

    # ── 8. HTF alignment (0-8 points) ───────────────
    if htf_bias and "error" not in htf_bias:
        htf_label = htf_bias.get("bias", "")
        if conf_direction == "bullish" and "BULLISH" in htf_label.upper():
            raw_score += 8
            factors.append("✅ HTF daily bias confirms bullish +8")
        elif conf_direction == "bearish" and "BEARISH" in htf_label.upper():
            raw_score += 8
            factors.append("✅ HTF daily bias confirms bearish +8")
        elif "NEUTRAL" in htf_label.upper():
            raw_score += 1
            factors.append("⚠️ HTF neutral — no strong context +1")
        else:
            raw_score -= 4
            factors.append("❌ HTF bias conflicts with signal -4")

    # ── 9. NEW: Harmonic Pattern confirmation (0-7 pts)
    if harmonic_data and harmonic_data.get("count", 0) > 0:
        h_bias = harmonic_data.get("bias", "neutral")
        h_count = harmonic_data.get("count", 0)
        if h_bias == conf_direction and conf_direction != "neutral":
            pts = min(h_count * 3, 7)
            raw_score += pts
            factors.append(f"✅ 🔷 Harmonic pattern confirms {conf_direction} +{pts}")
        elif h_bias != "neutral" and h_bias != conf_direction:
            raw_score -= 3
            factors.append(f"❌ 🔷 Harmonic pattern conflicts ({h_bias}) -3")

    # ── 10. NEW: Order Flow / Whale activity (0-7 pts)
    if order_flow_data:
        whale_score = order_flow_data.get("whale_score", 0)
        of_bias = order_flow_data.get("bias", "neutral")
        if whale_score >= 40:
            if of_bias == conf_direction and conf_direction != "neutral":
                pts = min(whale_score // 15, 7)
                raw_score += pts
                factors.append(f"✅ 🐋 Whale activity confirms {conf_direction} +{pts}")
            elif of_bias != "neutral" and of_bias != conf_direction:
                raw_score -= 3
                factors.append(f"❌ 🐋 Whale activity conflicts ({of_bias}) -3")
        elif whale_score >= 15:
            factors.append(f"⚠️ 🐳 Minor whale activity detected (score: {whale_score})")

    # ── 11. NEW: ML Prediction agreement (0-6 pts)
    if ml_data and ml_data.get("prediction") != "N/A":
        ml_dir = ml_data.get("direction_raw", "")
        ml_conf = ml_data.get("confidence", 0)
        ml_acc = ml_data.get("accuracy", 0)

        if ml_acc >= 55 and ml_conf >= 60:
            if (ml_dir == "UP" and conf_direction == "bullish") or \
               (ml_dir == "DOWN" and conf_direction == "bearish"):
                pts = 6 if ml_conf >= 70 else 4
                raw_score += pts
                factors.append(f"✅ 🤖 ML confirms {conf_direction} ({ml_conf}% conf, {ml_acc}% acc) +{pts}")
            else:
                raw_score -= 2
                factors.append(f"❌ 🤖 ML disagrees — predicts {ml_dir} ({ml_conf}%) -2")

    # ── 12. NEW: Session suitability (0-5 pts)
    if session_data and "error" not in session_data:
        session_adj = session_data.get("confidence_adjustment", 0)
        if session_adj >= 3:
            raw_score += 5
            factors.append(f"✅ ⏰ Peak trading session ({session_data.get('label', '')}) +5")
        elif session_adj >= 1:
            raw_score += 2
            factors.append(f"✅ ⏰ Active session ({session_data.get('label', '')}) +2")
        elif session_adj <= -3:
            raw_score -= 3
            factors.append(f"❌ ⏰ Off-hours / low liquidity ({session_data.get('label', '')}) -3")

    # ── Clamp and compute grade ──────────────────────
    confidence = max(0, min(100, raw_score))
    confidence = round(confidence, 1)
    grade = _score_to_grade(confidence)

    return {
        "confidence_pct": confidence,
        "grade": grade,
        "factors": factors,
        "factor_count": len([f for f in factors if f.startswith("✅")]),
        "warning_count": len([f for f in factors if f.startswith("❌") or f.startswith("⚠️")]),
    }


def _score_to_grade(confidence: float) -> str:
    if confidence >= 90: return "A+"
    if confidence >= 80: return "A"
    if confidence >= 70: return "B+"
    if confidence >= 60: return "B"
    if confidence >= 50: return "C+"
    if confidence >= 40: return "C"
    if confidence >= 30: return "D"
    return "F"


def grade_emoji(grade: str) -> str:
    """Return emoji for grade display."""
    emojis = {
        "A+": "🏆", "A": "🥇", "B+": "🥈", "B": "🥉",
        "C+": "✅", "C": "⚠️", "D": "🔸", "F": "❌",
    }
    return emojis.get(grade, "❓")
