"""
Signal Quality Grader
Assigns A+ to F letter grades and confidence percentages to signals.
Grades are computed from:
  1. Confluence score strength (|score| / 10)
  2. Multi-timeframe alignment
  3. Volume confirmation
  4. Pattern quality (high-reliability patterns score more)
  5. Divergence confirmation
  6. Trend strength (ADX)
  7. OB/FVG proximity (SMC confluence)
  8. Regime suitability

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
) -> dict:
    """
    Compute signal confidence (0-100%) and letter grade.

    Returns:
        confidence_pct: 0-100
        grade: "A+" to "F"
        factors: list of contributing factor descriptions
    """
    factors = []
    raw_score = 0.0

    # ── 1. Confluence strength (0-30 points) ─────────
    conf_abs = abs(confluence_score)
    conf_pts = min(conf_abs / 10.0 * 30, 30)
    raw_score += conf_pts
    if conf_abs >= 7:
        factors.append(f"✅ Strong confluence ({confluence_score:+d}/10) +{conf_pts:.0f}")
    elif conf_abs >= 4:
        factors.append(f"✅ Moderate confluence ({confluence_score:+d}/10) +{conf_pts:.0f}")
    elif conf_abs >= 1:
        factors.append(f"⚠️ Weak confluence ({confluence_score:+d}/10) +{conf_pts:.0f}")
    else:
        factors.append(f"❌ No directional confluence (0/10)")

    # ── 2. Volume confirmation (0-15 points) ─────────
    vol_trend = volume_data.get("trend", "")
    vol_spike = volume_data.get("spike", "")
    vol_pts = 0
    if "Rising" in vol_trend:
        vol_pts += 8
        factors.append("✅ Rising volume confirms move +8")
    elif "Declining" in vol_trend:
        vol_pts -= 5
        factors.append("❌ Declining volume weakens signal -5")
    if "Spike" in vol_spike:
        vol_pts += 7
        factors.append("✅ Volume spike detected +7")
    raw_score += max(0, vol_pts)

    # ── 3. Candlestick patterns (0-15 points) ────────
    pat_pts = 0
    for p in patterns[:3]:  # Max 3 patterns counted
        pname = p["pattern"].split("🟢")[0].split("🔴")[0].split("⚪")[0].strip()
        pname = pname.rstrip(" 🔨💫🔼🪢🔥💀🌱🍂🏔️🏝️🌅🌆🪖🐦")
        # Check if it's a high-reliability pattern
        is_hr = any(hr in p["pattern"] for hr in HIGH_RELIABILITY_PATTERNS)
        if is_hr:
            pat_pts += 5
            factors.append(f"✅ High-reliability: {p['pattern']} +5")
        else:
            pat_pts += 3
    raw_score += min(pat_pts, 15)

    # ── 4. Divergence (0-12 points) ──────────────────
    all_divs = div_rsi.get("divergences", []) + div_macd.get("divergences", [])
    div_pts = 0
    for d in all_divs[:2]:
        if "Regular" in d["type"]:
            div_pts += 6
            factors.append(f"✅ {d['type']} (strong reversal) +6")
        elif "Hidden" in d["type"]:
            div_pts += 4
            factors.append(f"✅ {d['type']} (continuation) +4")
    raw_score += min(div_pts, 12)

    # ── 5. Trend strength / ADX (0-10 points) ────────
    adx_val = trend_data.get("adx", {}).get("adx", 0)
    if adx_val >= 30:
        raw_score += 10
        factors.append(f"✅ Strong trend (ADX {adx_val}) +10")
    elif adx_val >= 25:
        raw_score += 7
        factors.append(f"✅ Trending (ADX {adx_val}) +7")
    elif adx_val >= 15:
        raw_score += 3
        factors.append(f"⚠️ Weak trend (ADX {adx_val}) +3")
    else:
        factors.append(f"❌ No trend (ADX {adx_val})")

    # ── 6. OB/FVG proximity — SMC confluence (0-10 pts)
    smc_pts = 0
    if ob_data.get("at_ob"):
        smc_pts += 6
        factors.append(f"✅ Price at Order Block +6")
    elif ob_data.get("nearest_bull") or ob_data.get("nearest_bear"):
        smc_pts += 2
        factors.append("⚠️ Near Order Block +2")
    if fvg_data.get("at_fvg"):
        smc_pts += 4
        factors.append(f"✅ Price inside FVG +4")
    raw_score += min(smc_pts, 10)

    # ── 7. Regime suitability (0-8 points) ───────────
    regime = regime_data.get("regime", "RANGING")
    conf_direction = "bullish" if confluence_score > 0 else "bearish" if confluence_score < 0 else "neutral"

    if regime == "TRENDING_UP" and conf_direction == "bullish":
        raw_score += 8
        factors.append("✅ Bullish signal in uptrend regime +8")
    elif regime == "TRENDING_DOWN" and conf_direction == "bearish":
        raw_score += 8
        factors.append("✅ Bearish signal in downtrend regime +8")
    elif regime in ("TRENDING_UP", "TRENDING_DOWN"):
        # Counter-trend signal
        raw_score -= 5
        factors.append("❌ Counter-trend signal: regime mismatch -5")
    elif regime == "QUIET":
        raw_score += 2
        factors.append("⚠️ Quiet regime: breakout watch +2")
    elif regime == "VOLATILE":
        raw_score -= 3
        factors.append("⚠️ Volatile regime: noise risk -3")

    # ── 8. HTF alignment bonus (0-10 points) ─────────
    if htf_bias and "error" not in htf_bias:
        htf_label = htf_bias.get("bias", "")
        if conf_direction == "bullish" and "BULLISH" in htf_label.upper():
            raw_score += 10
            factors.append("✅ HTF daily bias confirms bullish +10")
        elif conf_direction == "bearish" and "BEARISH" in htf_label.upper():
            raw_score += 10
            factors.append("✅ HTF daily bias confirms bearish +10")
        elif "NEUTRAL" in htf_label.upper():
            raw_score += 2
            factors.append("⚠️ HTF neutral — no strong context +2")
        else:
            raw_score -= 5
            factors.append("❌ HTF bias conflicts with signal -5")

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
