"""
Enhanced Confluence Scoring Engine
Aggregates signals from ALL analysis modules into a single bias score.
Now includes: OB/FVG scoring, Stochastic, trend strength weighting, HTF alignment.

Score range: -10 (max bearish) to +10 (max bullish)
Bias:
  +7 to +10 → Strong Buy
  +4 to +6  → Bullish
  +1 to +3  → Weak Bullish
  0          → Neutral
  -1 to -3  → Weak Bearish
  -4 to -6  → Bearish
  -7 to -10 → Strong Sell
"""


def score_market_structure(ms: dict) -> tuple[int, list]:
    """Score based on market structure."""
    notes = []
    score = 0
    trend = ms.get("trend", "")

    if "Uptrend" in trend:
        score += 2
        notes.append("✅ Uptrend (+2)")
    elif "Downtrend" in trend:
        score -= 2
        notes.append("❌ Downtrend (-2)")

    bos = ms.get("bos_choch", "None")
    if "BOS UP" in bos:
        score += 2
        notes.append("✅ Bullish BOS (+2)")
    elif "BOS DOWN" in bos:
        score -= 2
        notes.append("❌ Bearish BOS (-2)")

    seq = ms.get("structure_sequence", [])
    if "HH (Higher High)" in seq:
        score += 1
        notes.append("✅ Higher High (+1)")
    if "HL (Higher Low)" in seq:
        score += 1
        notes.append("✅ Higher Low (+1)")
    if "LH (Lower High)" in seq:
        score -= 1
        notes.append("❌ Lower High (-1)")
    if "LL (Lower Low)" in seq:
        score -= 1
        notes.append("❌ Lower Low (-1)")

    return score, notes


def score_indicators(ind: dict) -> tuple[int, list]:
    """Score RSI, MACD, EMA, Stochastic."""
    notes = []
    score = 0

    # RSI
    rsi_val = ind["rsi"]["value"]
    rsi_dir = ind["rsi"]["direction"]
    if rsi_val < 30:
        score += 2
        notes.append(f"✅ RSI Oversold ({rsi_val}) (+2)")
    elif rsi_val > 70:
        score -= 2
        notes.append(f"❌ RSI Overbought ({rsi_val}) (-2)")
    elif rsi_val > 55 and "Rising" in rsi_dir:
        score += 1
        notes.append(f"✅ RSI Bullish Zone + Rising (+1)")
    elif rsi_val < 45 and "Falling" in rsi_dir:
        score -= 1
        notes.append(f"❌ RSI Bearish Zone + Falling (-1)")

    # MACD
    macd = ind["macd"]
    if "Bullish Crossover" in macd["crossover"]:
        score += 2
        notes.append("✅ MACD Bullish Crossover (+2)")
    elif "Bearish Crossover" in macd["crossover"]:
        score -= 2
        notes.append("❌ MACD Bearish Crossover (-2)")
    elif "Bullish" in macd["momentum"]:
        score += 1
        notes.append("✅ MACD Bullish Momentum (+1)")
    elif "Bearish" in macd["momentum"]:
        score -= 1
        notes.append("❌ MACD Bearish Momentum (-1)")

    # EMA
    ema = ind["ema"]
    if "Strong Uptrend" in ema["trend"]:
        score += 2
        notes.append("✅ Strong EMA Uptrend (+2)")
    elif "Strong Downtrend" in ema["trend"]:
        score -= 2
        notes.append("❌ Strong EMA Downtrend (-2)")
    elif "Bullish Bias" in ema["trend"]:
        score += 1
        notes.append("✅ Above EMA200 (+1)")
    elif "Bearish Bias" in ema["trend"]:
        score -= 1
        notes.append("❌ Below EMA200 (-1)")

    if "Golden Cross" in ema.get("cross", ""):
        score += 1
        notes.append("✅ Golden Cross (+1)")
    elif "Death Cross" in ema.get("cross", ""):
        score -= 1
        notes.append("❌ Death Cross (-1)")

    # Stochastic (NEW)
    stoch = ind.get("stochastic", {})
    if stoch:
        stoch_cross = stoch.get("cross", "None")
        stoch_zone = stoch.get("zone", "")
        if "Bullish Crossover" in stoch_cross and "Oversold" in stoch_zone:
            score += 2
            notes.append("✅ Stoch Bullish Cross from Oversold (+2)")
        elif "Bearish Crossover" in stoch_cross and "Overbought" in stoch_zone:
            score -= 2
            notes.append("❌ Stoch Bearish Cross from Overbought (-2)")
        elif "Bullish" in stoch_cross:
            score += 1
            notes.append("✅ Stoch Bullish Crossover (+1)")
        elif "Bearish" in stoch_cross:
            score -= 1
            notes.append("❌ Stoch Bearish Crossover (-1)")

    return score, notes


def score_volume(vol: dict) -> tuple[int, list]:
    """Score volume trend."""
    notes = []
    score = 0

    if "Rising" in vol["trend"]:
        score += 1
        notes.append("✅ Rising Volume (+1)")
    elif "Declining" in vol["trend"]:
        score -= 1
        notes.append("❌ Declining Volume (-1)")

    if "Volume Spike" in vol["spike"]:
        score += 1
        notes.append("✅ Volume Spike (+1)")

    return score, notes


def score_patterns(patterns: list) -> tuple[int, list]:
    """Score candlestick patterns."""
    notes = []
    score = 0
    for p in patterns:
        if p["type"] == "bullish":
            score += 1
            notes.append(f"✅ {p['pattern']} (+1)")
        elif p["type"] == "bearish":
            score -= 1
            notes.append(f"❌ {p['pattern']} (-1)")
    return score, notes


def score_divergence(div_rsi: dict, div_macd: dict) -> tuple[int, list]:
    """Score divergence signals."""
    notes = []
    score = 0

    for div in div_rsi.get("divergences", []) + div_macd.get("divergences", []):
        t = div["type"]
        if "Regular Bullish" in t:
            score += 2
            notes.append(f"✅ {t} (+2)")
        elif "Regular Bearish" in t:
            score -= 2
            notes.append(f"❌ {t} (-2)")
        elif "Hidden Bullish" in t:
            score += 1
            notes.append(f"✅ {t} (+1)")
        elif "Hidden Bearish" in t:
            score -= 1
            notes.append(f"❌ {t} (-1)")

    return score, notes


def score_fibonacci(fib: dict, current_price: float) -> tuple[int, list]:
    """Score Fibonacci proximity (golden zone is high-value)."""
    notes = []
    score = 0

    if fib.get("golden_zone"):
        direction = fib.get("direction", "")
        if direction == "up":
            score += 2
            notes.append("✅ Price at Fibonacci Golden Zone (support) (+2)")
        else:
            score -= 2
            notes.append("❌ Price at Fibonacci Golden Zone (resistance) (-2)")
    elif fib.get("proximity_pct", 100) < 1.0:
        notes.append(f"📐 Near Fib {fib.get('nearest_level')} ({fib.get('proximity_pct')}%)")

    return score, notes


def score_liquidity(liq: dict, current_price: float) -> tuple[int, list]:
    """Score liquidity — proximity to pools can mean stop hunt risk."""
    notes = []
    score = 0

    buy_liq = liq.get("nearest_buy_liq")
    sell_liq = liq.get("nearest_sell_liq")

    if buy_liq and abs(current_price - buy_liq) / current_price < 0.005:
        score -= 1
        notes.append("⚠️ Near Buy-Side Liquidity (stop hunt risk) (-1)")

    if sell_liq and abs(current_price - sell_liq) / current_price < 0.005:
        score += 1
        notes.append("⚠️ Near Sell-Side Liquidity (potential bounce) (+1)")

    hunts = liq.get("stop_hunts", [])
    if hunts:
        last = hunts[-1]
        if "Bullish" in last["type"]:
            score += 1
            notes.append("✅ Recent Bullish Stop Hunt (smart money entry) (+1)")
        elif "Bearish" in last["type"]:
            score -= 1
            notes.append("❌ Recent Bearish Stop Hunt (-1)")

    return score, notes


def score_order_blocks(ob: dict, current_price: float) -> tuple[int, list]:
    """Score Order Block proximity (NEW)."""
    notes = []
    score = 0

    at_ob = ob.get("at_ob", "")
    if at_ob:
        if "Bullish" in at_ob:
            score += 2
            notes.append("✅ Price at Bullish Order Block (+2)")
        elif "Bearish" in at_ob:
            score -= 2
            notes.append("❌ Price at Bearish Order Block (-2)")

    # Nearest unmitigated OBs as support/resistance
    nb = ob.get("nearest_bull")
    nbe = ob.get("nearest_bear")
    if nb and not at_ob:
        dist = abs(current_price - nb["mid"]) / current_price
        if dist < 0.01:  # Within 1%
            score += 1
            notes.append("✅ Near Bullish OB (demand zone) (+1)")
    if nbe and not at_ob:
        dist = abs(current_price - nbe["mid"]) / current_price
        if dist < 0.01:
            score -= 1
            notes.append("❌ Near Bearish OB (supply zone) (-1)")

    return score, notes


def score_fvg(fvg: dict, current_price: float) -> tuple[int, list]:
    """Score Fair Value Gap proximity (NEW)."""
    notes = []
    score = 0

    at_fvg = fvg.get("at_fvg", "")
    if at_fvg:
        if "Bullish" in at_fvg:
            score += 1
            notes.append("✅ Price inside Bullish FVG (support) (+1)")
        elif "Bearish" in at_fvg:
            score -= 1
            notes.append("❌ Price inside Bearish FVG (resistance) (-1)")

    return score, notes


def get_bias_label(score: int) -> str:
    if score >= 7:
        return "🚀 STRONG BUY"
    elif score >= 4:
        return "🟢 BULLISH"
    elif score >= 1:
        return "📗 Weak Bullish"
    elif score == 0:
        return "⚪ NEUTRAL"
    elif score >= -3:
        return "📕 Weak Bearish"
    elif score >= -6:
        return "🔴 BEARISH"
    else:
        return "💀 STRONG SELL"


def calculate_confluence(
    ms: dict,
    indicators: dict,
    patterns: list,
    liquidity: dict,
    fib: dict,
    div_rsi: dict,
    div_macd: dict,
    current_price: float,
    order_blocks: dict = None,
    fvg: dict = None,
    htf_bias: dict = None,
) -> dict:
    """Master confluence scorer. Returns score, label, and breakdown."""
    all_notes = []
    total_score = 0

    s, n = score_market_structure(ms)
    total_score += s; all_notes += n

    s, n = score_indicators(indicators)
    total_score += s; all_notes += n

    s, n = score_volume(indicators["volume"])
    total_score += s; all_notes += n

    s, n = score_patterns(patterns)
    total_score += s; all_notes += n

    s, n = score_divergence(div_rsi, div_macd)
    total_score += s; all_notes += n

    s, n = score_fibonacci(fib, current_price)
    total_score += s; all_notes += n

    s, n = score_liquidity(liquidity, current_price)
    total_score += s; all_notes += n

    # ── NEW: Order Block scoring ─────────────────────
    if order_blocks:
        s, n = score_order_blocks(order_blocks, current_price)
        total_score += s; all_notes += n

    # ── NEW: FVG scoring ─────────────────────────────
    if fvg:
        s, n = score_fvg(fvg, current_price)
        total_score += s; all_notes += n

    # ── NEW: HTF alignment bonus ─────────────────────
    if htf_bias and "error" not in htf_bias:
        htf_label = htf_bias.get("bias", "")
        if total_score > 0 and "BULLISH" in htf_label.upper():
            total_score += 1
            all_notes.append("✅ HTF daily confirms bullish (+1)")
        elif total_score < 0 and "BEARISH" in htf_label.upper():
            total_score -= 1
            all_notes.append("✅ HTF daily confirms bearish (-1)")
        elif total_score > 0 and "BEARISH" in htf_label.upper():
            total_score -= 1
            all_notes.append("⚠️ HTF conflicts — daily bearish (-1)")
        elif total_score < 0 and "BULLISH" in htf_label.upper():
            total_score += 1
            all_notes.append("⚠️ HTF conflicts — daily bullish (+1)")

    # Clamp to -10..+10
    total_score = max(-10, min(10, total_score))
    bias = get_bias_label(total_score)

    return {
        "score": total_score,
        "bias": bias,
        "breakdown": all_notes,
        "bullish_signals": len([n for n in all_notes if n.startswith("✅")]),
        "bearish_signals": len([n for n in all_notes if n.startswith("❌")]),
    }
