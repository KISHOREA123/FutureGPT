def fmt_score_bar(score: int) -> str:
    filled = abs(score)
    empty = 10 - filled
    if score >= 0:
        bar = "🟩" * filled + "⬜" * empty
        return f"[{bar}] +{score}/10"
    else:
        bar = "⬜" * empty + "🟥" * filled
        return f"[{bar}] {score}/10"


def fmt_price(p) -> str:
    if p is None:
        return "N/A"
    p = float(p)
    if p >= 1000:
        return f"${p:,.2f}"
    elif p >= 1:
        return f"${p:.4f}"
    else:
        return f"${p:.8f}"


def format_full_analysis(results: dict) -> str:
    """
    Compact full analysis — tight, scannable, no noise.
    Includes ATR, BB squeeze, Order Blocks, FVG, and HTF bias.
    """
    lines = []

    # ── HTF Daily Bias (once, at the top) ───────────────────
    htf = results.get("__htf__", {})
    if htf and "error" not in htf:
        # Peek at symbol from first valid TF
        sym_hint = next((d["symbol"] for tf, d in results.items()
                         if tf != "__htf__" and "error" not in d), "")
        if sym_hint:
            lines.append(format_htf_bias(htf, sym_hint))

    for tf, data in results.items():
        if tf == "__htf__":
            continue
        if "error" in data:
            lines.append(f"⚠️ *[{tf}]* {data['error']}")
            continue

        sym   = data["symbol"]
        price = fmt_price(data["current_price"])
        exch  = data["exchange"].capitalize()
        ms    = data["market_structure"]
        sr    = data["support_resistance"]
        liq   = data["liquidity"]
        vol   = data["indicators"]["volume"]
        rsi   = data["indicators"]["rsi"]
        macd  = data["indicators"]["macd"]
        ema   = data["indicators"]["ema"]
        pats  = data["candlestick_patterns"]
        fib   = data.get("fibonacci", {})
        div   = data.get("divergence", {})
        conf  = data.get("confluence", {})
        atr   = data.get("atr", {})
        bb    = data.get("bollinger", {})
        ob    = data.get("order_blocks", {})
        fvg   = data.get("fvg", {})

        # NEW data sources
        trend_s = data.get("trend_strength", {})
        regime  = data.get("regime", {})
        setup   = data.get("trade_setup", {})
        stoch   = data.get("indicators", {}).get("stochastic", {})
        grade_d = setup.get("grade", {}) if setup else {}

        # ── Header with grade pill ───────────────────────────
        grade_str = ""
        if grade_d and grade_d.get("grade"):
            from analysis.signal_grader import grade_emoji
            g = grade_d["grade"]
            ge = grade_emoji(g)
            c_pct = grade_d.get("confidence_pct", 0)
            grade_str = f"  ·  {ge} *{g}* ({c_pct}%)"
        lines.append(f"*{sym}/USDT* `{tf}` · *{price}* · _{exch}_{grade_str}")

        # ── Confluence bar ───────────────────────────────────
        score  = conf.get("score", 0)
        bias   = conf.get("bias", "N/A")
        filled = "█" * abs(score)
        empty  = "░" * (10 - abs(score))
        sign   = "[+]" if score >= 0 else "[-]"
        lines.append(f"`{sign} {filled}{empty} {score:+d}/10`  {bias}")

        # ── Regime tag ───────────────────────────────────────
        if regime:
            lines.append(f"  {regime.get('label', '')}")
        lines.append("")

        # ── Trend & BOS ──────────────────────────────────────
        seq = " · ".join(ms.get("structure_sequence", [])) or "—"
        lines.append(f"📊 {ms['trend']}  ·  _{seq}_")
        bos = ms.get("bos_choch", "None")
        if bos != "None":
            lines.append(f"   ↳ {bos}")

        # ── Key Levels ───────────────────────────────────────
        lines.append("")
        lines.append("📍 *Levels*")
        nr = sr.get("nearest_resistance")
        ns = sr.get("nearest_support")
        if nr:
            lines.append(f"  🔴 R: {fmt_price(nr['level'])}  ({nr['strength']})")
        if ns:
            lines.append(f"  🟢 S: {fmt_price(ns['level'])}  ({ns['strength']})")

        if fib and fib.get("proximity_pct", 100) < 2.0:
            gz = "  🌟 Golden Zone" if fib.get("golden_zone") else ""
            lines.append(f"  📐 Fib {fib['nearest_level']} → {fmt_price(fib['nearest_price'])}{gz}")

        bl = liq.get("nearest_buy_liq")
        sl_liq = liq.get("nearest_sell_liq")
        pool_parts = []
        if bl: pool_parts.append(f"↑{fmt_price(bl)}")
        if sl_liq: pool_parts.append(f"↓{fmt_price(sl_liq)}")
        if pool_parts:
            lines.append(f"  💧 Liq: {' · '.join(pool_parts)}")

        hunts = liq.get("stop_hunts", [])
        if hunts:
            h = hunts[-1]
            lines.append(f"  ⚡ Hunt: {h['type']} @ {fmt_price(h['price'])}")

        # ── Order Blocks & FVG (compact inline) ─────────────
        ob_lines  = _fmt_ob_section(ob)
        fvg_lines = _fmt_fvg_section(fvg)
        if ob_lines or fvg_lines:
            lines.append("")
            lines.append("🧱 *OB / FVG*")
            lines.extend(ob_lines)
            lines.extend(fvg_lines)

        # ── Indicators ───────────────────────────────────────
        lines.append("")
        lines.append("📈 *Indicators*")

        lines.append(f"  RSI {rsi['value']} · {rsi['zone'].split('Zone')[0].strip()} · {rsi['direction']}")

        if macd["crossover"] != "None":
            lines.append(f"  MACD {macd['crossover']}")
        else:
            lines.append(f"  MACD {macd['momentum']} · Hist {macd['histogram_trend']}")

        ema_label = ema["trend"].split("(")[0].strip()
        lines.append(f"  EMA {ema_label}")
        if ema["cross"] != "None":
            lines.append(f"   ↳ {ema['cross']}")

        if "Rising" in vol["trend"] or "Declining" in vol["trend"]:
            vol_label = vol["trend"].split("(")[0].strip()
            spike = f" · {vol['spike']}" if "Spike" in vol["spike"] else ""
            lines.append(f"  Vol {vol_label}{spike}")
        if "Climax" in vol.get("climax_candle", ""):
            lines.append(f"  ⚠️ {vol['climax_candle']}")

        # Stochastic
        if stoch and stoch.get("cross") != "None":
            lines.append(f"  Stoch %K={stoch['k']} %D={stoch['d']} · {stoch['zone']}")
            lines.append(f"   ↳ {stoch['cross']}")

        # ADX / Trend Strength
        if trend_s:
            adx = trend_s.get("adx", {})
            lines.append(f"  ADX {adx.get('adx', 0)} · {adx.get('strength', '')}")
            if adx.get("di_cross") != "None":
                lines.append(f"   ↳ {adx['di_cross']}")

        # ATR — always show (key for SL)
        if atr:
            lines.append(f"  ATR {fmt_price(atr.get('atr', 0))} ({atr.get('atr_pct')}%)  ·  {atr.get('volatility', '')}")
            lines.append(f"   ↳ SL Long: {atr.get('sl_1x')}  ·  Short: {atr.get('sl_1x_short')}")

        # BB — only show squeeze or notable position
        if bb:
            sq = bb.get("squeeze", "")
            pos = bb.get("position", "")
            if sq != "No squeeze":
                lines.append(f"  BB ⚡ {sq}")
            elif "Above" in pos or "Below" in pos:
                lines.append(f"  BB {pos}")

        # ── Signals ──────────────────────────────────────────
        signals = []
        for p in pats:
            e = "🟢" if p["type"] == "bullish" else "🔴" if p["type"] == "bearish" else "⚪"
            signals.append(f"{e} {p['pattern']}")

        all_divs = (
            div.get("rsi", {}).get("divergences", []) +
            div.get("macd", {}).get("divergences", [])
        )
        for d in all_divs:
            parts = d["type"].split()
            short = " ".join(parts[:3])
            signals.append(f"{short} Div [{d['indicator']}]")

        if signals:
            lines.append("")
            lines.append("🕯 *Signals*")
            for s in signals[:4]:
                lines.append(f"  {s}")

        lines.append("")
        lines.append("─" * 30)
        lines.append("")

    return "\n".join(lines)


def format_sr_only(results: dict) -> str:
    lines = []
    for tf, data in results.items():
        if tf == "__htf__":
            continue
        if "error" in data:
            lines.append(f"⚠️ [{tf}] {data['error']}")
            continue
        sym = data["symbol"]
        sr  = data["support_resistance"]
        lines.append(f"*{sym}/USDT* `{tf}` · {fmt_price(data['current_price'])}")
        lines.append("🔴 *Resistance*")
        for r in sr["resistance"]:
            lines.append(f"  {fmt_price(r['level'])}  {r['strength']} · {r['touches']}t")
        lines.append("🟢 *Support*")
        for s in sr["support"]:
            lines.append(f"  {fmt_price(s['level'])}  {s['strength']} · {s['touches']}t")
        lines.append("")
    return "\n".join(lines)


def format_patterns_only(results: dict) -> str:
    lines = []
    for tf, data in results.items():
        if tf == "__htf__":
            continue
        if "error" in data:
            lines.append(f"⚠️ [{tf}] {data['error']}")
            continue
        sym  = data["symbol"]
        pats = data["candlestick_patterns"]
        lines.append(f"*{sym}/USDT* `{tf}`")
        if pats:
            for p in pats:
                e = "🟢" if p["type"] == "bullish" else "🔴" if p["type"] == "bearish" else "⚪"
                lines.append(f"  {e} {p['pattern']}")
        else:
            lines.append("  No significant pattern.")
        lines.append("")
    return "\n".join(lines)


def format_liquidity_only(results: dict) -> str:
    lines = []
    for tf, data in results.items():
        if tf == "__htf__":
            continue
        if "error" in data:
            lines.append(f"⚠️ [{tf}] {data['error']}")
            continue
        sym  = data["symbol"]
        liq  = data["liquidity"]
        price = fmt_price(data["current_price"])
        lines.append(f"*{sym}/USDT* `{tf}` · {price}")

        bl = liq.get("buy_side_liquidity", [])
        sl = liq.get("sell_side_liquidity", [])
        if bl:
            lines.append(f"🔺 Buy-Side (above): {' · '.join(fmt_price(l) for l in bl[:3])}")
        if sl:
            lines.append(f"🔻 Sell-Side (below): {' · '.join(fmt_price(l) for l in sl[:3])}")

        hunts = liq.get("stop_hunts", [])
        if hunts:
            for h in hunts[-2:]:
                lines.append(f"⚡ {h['type']} @ {fmt_price(h['price'])}  ({h['time']})")
        else:
            lines.append("No recent stop hunts.")
        lines.append("")
    return "\n".join(lines)


def format_summary(results: dict) -> str:
    """Quick bias snapshot — ultra compact."""
    lines = []
    sym = None

    for tf, data in results.items():
        if tf == "__htf__":
            continue
        if "error" in data:
            lines.append(f"⚠️ [{tf}] {data['error']}")
            continue

        if sym is None:
            sym = data["symbol"]
            lines.append(f"*{sym}/USDT — Bias Summary*\n")

        price = fmt_price(data["current_price"])
        conf  = data.get("confluence", {})
        score = conf.get("score", 0)
        bias  = conf.get("bias", "N/A")
        ms    = data["market_structure"]
        rsi   = data["indicators"]["rsi"]
        ema   = data["indicators"]["ema"]
        vol   = data["indicators"]["volume"]
        pats  = data["candlestick_patterns"]
        all_divs = (
            data.get("divergence", {}).get("rsi", {}).get("divergences", []) +
            data.get("divergence", {}).get("macd", {}).get("divergences", [])
        )
        fib = data.get("fibonacci", {})

        filled = "█" * abs(score)
        empty  = "░" * (10 - abs(score))
        sign   = "[+]" if score >= 0 else "[-]"

        lines.append(f"`{tf}` *{price}*  ·  {bias}")
        lines.append(f"`{sign} {filled}{empty} {score:+d}/10`")
        lines.append(f"  {ms['trend']}  ·  RSI {rsi['value']} {rsi['direction']}")
        ema_short = ema["trend"].split("(")[0].strip()
        lines.append(f"  {ema_short}")

        extras = []
        if pats:
            extras.append(pats[0]["pattern"])
        if all_divs:
            parts = all_divs[0]["type"].split()
            extras.append(" ".join(parts[:3]) + f" [{all_divs[0]['indicator']}]")
        if fib.get("golden_zone"):
            extras.append("📐 At Fib Golden Zone")
        bos = ms.get("bos_choch", "None")
        if bos != "None":
            extras.append(bos.split("(")[0].strip())
        if extras:
            lines.append(f"  ↳ {' · '.join(extras[:3])}")

        lines.append("")

    lines.append("_/analyze <coin> for full details_")
    return "\n".join(lines)


def format_scan_results(scan: dict) -> str:
    lines = [f"🔍 *Market Scan*  ·  {scan['scanned']} coins\n"]

    if scan["top_bullish"]:
        lines.append("🟢 *Bullish Setups*")
        for i, r in enumerate(scan["top_bullish"], 1):
            tf_str = "  ".join([f"{tf}:{v['score']:+d}" for tf, v in r["tf_biases"].items()])
            lines.append(f"  {i}. *{r['symbol']}*  `{r['avg_score']:+.1f}/10`  ·  {fmt_price(r['price'])}")
            lines.append(f"     {tf_str}")
        lines.append("")

    if scan["top_bearish"]:
        lines.append("🔴 *Bearish Setups*")
        for i, r in enumerate(scan["top_bearish"], 1):
            tf_str = "  ".join([f"{tf}:{v['score']:+d}" for tf, v in r["tf_biases"].items()])
            lines.append(f"  {i}. *{r['symbol']}*  `{r['avg_score']:+.1f}/10`  ·  {fmt_price(r['price'])}")
            lines.append(f"     {tf_str}")
        lines.append("")

    if not scan["top_bullish"] and not scan["top_bearish"]:
        lines.append("⚪ No strong setups found — market is mostly neutral.")

    lines.append("_/analyze <coin> for full breakdown_")
    return "\n".join(lines)


def format_fib_only(results: dict) -> str:
    lines = []
    for tf, data in results.items():
        if tf == "__htf__":
            continue
        if "error" in data:
            lines.append(f"⚠️ [{tf}] {data['error']}")
            continue
        sym   = data["symbol"]
        price = fmt_price(data["current_price"])
        fib   = data.get("fibonacci", {})
        if not fib:
            lines.append(f"*{sym}/USDT* `{tf}` — No Fib data.")
            continue

        direction = "↑ Retracing" if fib["direction"] == "up" else "↓ Bouncing"
        lines.append(f"*{sym}/USDT* `{tf}` · {price}  ·  {direction}")
        lines.append(f"  Swing: {fmt_price(fib['swing_low'])} → {fmt_price(fib['swing_high'])}")
        if fib.get("golden_zone"):
            lines.append("  🌟 *Price in Golden Zone (0.5–0.618)!*")
        lines.append("")
        lines.append("*Retracements:*")
        key_labels = ["23%", "38%", "50%", "61%", "78%"]
        for label, pv in fib["retracement_levels"].items():
            if any(k in label for k in key_labels):
                marker = " ← Price" if abs(pv - data["current_price"]) / data["current_price"] < 0.005 else ""
                lines.append(f"  {label:6s} {fmt_price(pv)}{marker}")
        lines.append("*Targets:*")
        for label, pv in list(fib["extension_levels"].items())[:3]:
            lines.append(f"  {label:10s} {fmt_price(pv)}")
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# NEW FEATURE FORMATTERS
# ─────────────────────────────────────────────────────────────

def format_htf_bias(htf: dict, symbol: str) -> str:
    """Compact HTF daily bias block — prepended to /analyze output."""
    if not htf or "error" in htf:
        return ""
    lines = [
        f"🌍 *HTF Daily Bias — {symbol}/USDT*",
        f"  {htf['bias']}  ·  {htf['ema_trend']}",
        f"  Structure: _{htf['structure']}_",
        f"  Last Daily Candle: {htf['candle']}",
        f"  Week Range: {htf['weekly_low']} – {htf['weekly_high']}",
        f"  D-EMA: 21={htf['ema21']} · 50={htf['ema50']} · 200={htf['ema200']}",
        "",
    ]
    return "\n".join(lines)


def _fmt_ob_section(ob_data: dict) -> list:
    """Format order blocks inline for /analyze."""
    lines = []
    nb = ob_data.get("nearest_bull")
    nbe = ob_data.get("nearest_bear")
    at = ob_data.get("at_ob")

    if at:
        lines.append(f"  ⚠️ {at}")
    if nb:
        lines.append(f"  🟢 Bull OB: {fmt_price(nb['low'])} – {fmt_price(nb['high'])}  {nb['status']}")
    if nbe:
        lines.append(f"  🔴 Bear OB: {fmt_price(nbe['low'])} – {fmt_price(nbe['high'])}  {nbe['status']}")
    return lines


def _fmt_fvg_section(fvg_data: dict) -> list:
    """Format FVGs inline for /analyze."""
    lines = []
    at  = fvg_data.get("at_fvg")
    abv = fvg_data.get("nearest_above")
    blw = fvg_data.get("nearest_below")

    if at:
        lines.append(f"  ⚠️ Price inside FVG: {at}")
    if abv:
        lines.append(f"  🔴 FVG above: {fmt_price(abv['low'])} – {fmt_price(abv['high'])}  ({abv['gap_pct']}%)")
    if blw:
        lines.append(f"  🟢 FVG below: {fmt_price(blw['low'])} – {fmt_price(blw['high'])}  ({blw['gap_pct']}%)")
    return lines


def format_ob_fvg_only(results: dict) -> str:
    """Dedicated /ob command — full order block + FVG breakdown."""
    lines = []
    for tf, data in results.items():
        if tf == "__htf__" or "error" in data:
            continue

        sym   = data["symbol"]
        price = fmt_price(data["current_price"])
        ob    = data.get("order_blocks", {})
        fvg   = data.get("fvg", {})

        lines.append(f"*{sym}/USDT* `{tf}` · {price}")

        # Order Blocks
        lines.append("🧱 *Order Blocks*")
        at_ob = ob.get("at_ob")
        if at_ob:
            lines.append(f"  ⚠️ {at_ob}")

        for item in ob.get("bullish_obs", [])[:2]:
            lines.append(f"  🟢 Bull: {fmt_price(item['low'])} – {fmt_price(item['high'])}  {item['status']}  (+{item['move_pct']}%)")
        for item in ob.get("bearish_obs", [])[:2]:
            lines.append(f"  🔴 Bear: {fmt_price(item['low'])} – {fmt_price(item['high'])}  {item['status']}  (-{item['move_pct']}%)")
        if ob.get("total_found", 0) == 0:
            lines.append("  No significant order blocks.")

        lines.append("")

        # FVGs
        lines.append("📭 *Fair Value Gaps*")
        at_fvg = fvg.get("at_fvg")
        if at_fvg:
            lines.append(f"  ⚠️ Price inside FVG!")
        for item in fvg.get("bearish_fvgs", [])[:2]:
            lines.append(f"  🔴 Above: {fmt_price(item['low'])} – {fmt_price(item['high'])}  {item['status']}  ({item['gap_pct']}%)")
        for item in fvg.get("bullish_fvgs", [])[:2]:
            lines.append(f"  🟢 Below: {fmt_price(item['low'])} – {fmt_price(item['high'])}  {item['status']}  ({item['gap_pct']}%)")
        if fvg.get("total_open", 0) == 0:
            lines.append("  No open FVGs detected.")

        lines.append("")
        lines.append("─" * 30)
        lines.append("")

    return "\n".join(lines)


def format_volatility_only(results: dict) -> str:
    """Dedicated /volatility command — ATR + Bollinger Bands."""
    lines = []
    for tf, data in results.items():
        if tf == "__htf__" or "error" in data:
            continue

        sym   = data["symbol"]
        price = fmt_price(data["current_price"])
        atr   = data.get("atr", {})
        bb    = data.get("bollinger", {})

        lines.append(f"*{sym}/USDT* `{tf}` · {price}")

        # ATR
        lines.append(f"📏 *ATR (14)*  ·  {fmt_price(atr.get('atr', 0))}  ({atr.get('atr_pct', 0)}% of price)")
        lines.append(f"  Volatility: {atr.get('volatility', 'N/A')}  ·  Ratio: {atr.get('atr_ratio', 0)}x avg")
        lines.append(f"  🛑 SL Ideas (Long):   1x={atr.get('sl_1x')}  ·  1.5x={atr.get('sl_15x')}  ·  2x={atr.get('sl_2x')}")
        lines.append(f"  🛑 SL Ideas (Short):  1x={atr.get('sl_1x_short')}  ·  2x={atr.get('sl_2x_short')}")

        lines.append("")

        # Bollinger Bands
        lines.append(f"📊 *Bollinger Bands (20, 2σ)*")
        lines.append(f"  Upper: {bb.get('upper')}  ·  Mid: {bb.get('mid')}  ·  Lower: {bb.get('lower')}")
        lines.append(f"  Position: {bb.get('position')}")
        lines.append(f"  %B: {bb.get('pct_b')}%  ·  Bandwidth: {bb.get('bandwidth_pct')}%")
        squeeze = bb.get("squeeze", "")
        if squeeze != "No squeeze":
            lines.append(f"  ⚡ {squeeze}")

        lines.append("")
        lines.append("─" * 30)
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# QUALITY UPGRADE FORMATTERS
# ─────────────────────────────────────────────────────────────

def format_trade_setup(results: dict) -> str:
    """Actionable trade card — /trade command."""
    from analysis.signal_grader import grade_emoji
    lines = []
    sym = None

    for tf, data in results.items():
        if tf == "__htf__" or "error" in data:
            continue

        if sym is None:
            sym = data["symbol"]

        setup = data.get("trade_setup", {})
        if not setup:
            lines.append(f"`{tf}` — No trade setup data.")
            continue

        price = fmt_price(data["current_price"])
        verdict = setup.get("verdict", "❓")
        grade_d = setup.get("grade", {})
        grade = grade_d.get("grade", "?")
        conf_pct = grade_d.get("confidence_pct", 0)
        pos = setup.get("position", {})
        regime = setup.get("regime", {})

        ge = grade_emoji(grade)
        lines.append(f"🎯 *{sym}/USDT Trade Setup* `{tf}`")
        lines.append(f"  {verdict}")
        lines.append(f"  {ge} Grade: *{grade}*  ·  Confidence: *{conf_pct}%*")
        lines.append(f"  📊 Confluence: `{setup.get('confluence_score', 0):+d}/10` {setup.get('confluence_bias', '')}")
        lines.append("")

        if regime:
            lines.append(f"  {regime.get('label', '')}")
            lines.append(f"  _Strategy: {regime.get('strategy', '')}_")
            lines.append("")

        if setup.get("tradeable") and pos and "error" not in pos:
            direction_emoji = "🟢 LONG" if pos.get("direction") == "BUY" else "🔴 SHORT"
            lines.append(f"  {direction_emoji}")
            lines.append(f"  Entry:  `{pos.get('entry', 'N/A')}`")
            lines.append(f"  SL:     `{pos.get('sl', 'N/A')}`  ({pos.get('sl_distance_pct', 0)}%)")
            lines.append(f"  TP1:    `{pos.get('tp1', 'N/A')}`  (1.5x R)")
            lines.append(f"  TP2:    `{pos.get('tp2', 'N/A')}`  (2.5x R)")
            lines.append(f"  R:R:    *{pos.get('rr_ratio', 0)}x*  {pos.get('rr_verdict', '')}")
            lines.append(f"  Size:   ${pos.get('position_size_usd', 0):,.2f}  ·  Risk: ${pos.get('risk_amount', 0):.2f}")
            lines.append(f"  Leverage: {pos.get('leverage', 1)}x")
        elif not setup.get("tradeable"):
            lines.append("  *Fail Reasons:*")
            for r in setup.get("fail_reasons", []):
                lines.append(f"   ❌ {r}")

        # Quality checks summary
        qc = setup.get("quality_checks", {})
        if qc:
            checks = []
            checks.append("✅" if qc.get("confluence_pass") else "❌")
            checks.append("✅" if qc.get("grade_pass") else "❌")
            checks.append("✅" if qc.get("confidence_pass") else "❌")
            checks.append("✅" if qc.get("rr_pass") else "❌")
            checks.append("✅" if qc.get("volume_pass") else "❌")
            checks.append("✅" if qc.get("regime_pass") else "❌")
            labels = ["Conf", "Grade", "Cnfd", "R:R", "Vol", "Rgme"]
            check_str = "  ".join(f"{c}{l}" for c, l in zip(checks, labels))
            lines.append("")
            lines.append(f"  `{check_str}`")

        lines.append("")
        lines.append("─" * 30)
        lines.append("")

    if not lines:
        lines.append("⚠️ No trade setup data available.")

    return "\n".join(lines)


def format_grade_only(results: dict) -> str:
    """Quick signal grade check — /grade command."""
    from analysis.signal_grader import grade_emoji
    lines = []
    sym = None

    for tf, data in results.items():
        if tf == "__htf__" or "error" in data:
            continue

        if sym is None:
            sym = data["symbol"]
            lines.append(f"🏆 *{sym}/USDT — Signal Quality*\n")

        setup = data.get("trade_setup", {})
        grade_d = setup.get("grade", {}) if setup else {}
        grade = grade_d.get("grade", "?")
        conf_pct = grade_d.get("confidence_pct", 0)
        ge = grade_emoji(grade)

        conf = data.get("confluence", {})
        score = conf.get("score", 0)
        bias = conf.get("bias", "")
        regime = data.get("regime", {})

        filled = "█" * abs(score)
        empty = "░" * (10 - abs(score))

        lines.append(f"`{tf}` {ge} *{grade}* · {conf_pct}%")
        lines.append(f"  `{filled}{empty}` {score:+d}/10 {bias}")
        if regime:
            lines.append(f"  {regime.get('label', '')}")

        # Top contributing factors
        factors = grade_d.get("factors", [])[:4]
        for f in factors:
            lines.append(f"  {f}")

        verdict = setup.get("verdict", "") if setup else ""
        if verdict:
            lines.append(f"  → {verdict}")
        lines.append("")

    lines.append("_/trade <coin> for full setup with entry/SL/TP_")
    return "\n".join(lines)


def format_report(results: dict) -> str:
    """
    Complete institution-grade chart analysis report.
    /report command — comprehensive multi-section analysis.
    """
    from analysis.signal_grader import grade_emoji
    lines = []

    # ── HTF Context ──────────────────────────────────────
    htf = results.get("__htf__", {})
    sym_hint = next((d["symbol"] for tf, d in results.items()
                     if tf != "__htf__" and "error" not in d), "COIN")

    lines.append(f"📋 *COMPLETE CHART REPORT*")
    lines.append(f"*{sym_hint}/USDT*")
    lines.append("═" * 30)
    lines.append("")

    if htf and "error" not in htf:
        lines.append("🌍 *SECTION 1: HIGHER TIMEFRAME CONTEXT*")
        lines.append(f"  Daily Bias: {htf['bias']}")
        lines.append(f"  EMA Trend: {htf['ema_trend']}")
        lines.append(f"  Structure: _{htf['structure']}_")
        lines.append(f"  Last Daily Candle: {htf['candle']}")
        lines.append(f"  Weekly Range: {htf['weekly_low']} – {htf['weekly_high']}")
        lines.append(f"  Volume: {htf.get('volume', 'N/A')}")
        lines.append(f"  D-EMA: 21={htf['ema21']} · 50={htf['ema50']} · 200={htf['ema200']}")
        lines.append("")
        lines.append("─" * 30)
        lines.append("")

    for tf, data in results.items():
        if tf == "__htf__" or "error" in data:
            continue

        sym = data["symbol"]
        price = fmt_price(data["current_price"])
        exch = data["exchange"].capitalize()
        ms = data["market_structure"]
        sr = data["support_resistance"]
        liq = data["liquidity"]
        ind = data["indicators"]
        pats = data["candlestick_patterns"]
        fib = data.get("fibonacci", {})
        div = data.get("divergence", {})
        conf = data.get("confluence", {})
        atr = data.get("atr", {})
        bb = data.get("bollinger", {})
        ob = data.get("order_blocks", {})
        fvg = data.get("fvg", {})
        trend_s = data.get("trend_strength", {})
        regime = data.get("regime", {})
        setup = data.get("trade_setup", {})
        grade_d = setup.get("grade", {}) if setup else {}
        stoch = ind.get("stochastic", {})

        grade = grade_d.get("grade", "?")
        ge = grade_emoji(grade)
        conf_pct = grade_d.get("confidence_pct", 0)
        score = conf.get("score", 0)

        lines.append(f"⏰ *TIMEFRAME: {tf.upper()}* · {price} · _{exch}_")
        lines.append(f"  {ge} Grade *{grade}* · Confidence *{conf_pct}%*")
        filled = "█" * abs(score)
        empty = "░" * (10 - abs(score))
        lines.append(f"  `{filled}{empty}` {score:+d}/10 {conf.get('bias', '')}")
        lines.append("")

        # ── Section: Market Structure ────────────────────
        lines.append("📊 *Market Structure*")
        seq = " · ".join(ms.get("structure_sequence", [])) or "—"
        lines.append(f"  Trend: {ms['trend']}")
        lines.append(f"  Sequence: _{seq}_")
        bos = ms.get("bos_choch", "None")
        if bos != "None":
            lines.append(f"  {bos}")
        lines.append("")

        # ── Section: Trend Strength ──────────────────────
        if trend_s:
            adx = trend_s.get("adx", {})
            slope = trend_s.get("ema_slope", {})
            lines.append("💪 *Trend Strength*")
            lines.append(f"  Trend Score: {trend_s.get('trend_score', 0)}/100 — {trend_s.get('quality', '')}")
            lines.append(f"  ADX: {adx.get('adx', 0)} · DI+: {adx.get('plus_di', 0)} · DI-: {adx.get('minus_di', 0)}")
            lines.append(f"  {adx.get('strength', '')} · {adx.get('direction', '')}")
            if adx.get("di_cross") != "None":
                lines.append(f"  {adx['di_cross']}")
            lines.append(f"  EMA Slope: {slope.get('slope_pct', 0)}% — {slope.get('label', '')}")
            lines.append("")

        # ── Section: Regime ──────────────────────────────
        if regime:
            lines.append("🌡️ *Market Regime*")
            lines.append(f"  {regime.get('label', '')}")
            lines.append(f"  _Strategy: {regime.get('strategy', '')}_")
            lines.append(f"  _{regime.get('advice', '')}_")
            lines.append("")

        # ── Section: Key Levels ──────────────────────────
        lines.append("📍 *Key Levels*")
        for r in sr.get("resistance", [])[:3]:
            lines.append(f"  🔴 R: {fmt_price(r['level'])}  {r['strength']} · {r['touches']}t")
        for s in sr.get("support", [])[:3]:
            lines.append(f"  🟢 S: {fmt_price(s['level'])}  {s['strength']} · {s['touches']}t")
        lines.append("")

        # ── Section: Fibonacci ───────────────────────────
        if fib:
            direction = "↑ Upswing" if fib.get("direction") == "up" else "↓ Downswing"
            lines.append(f"📐 *Fibonacci* — {direction}")
            gz = "  🌟 *GOLDEN ZONE!*" if fib.get("golden_zone") else ""
            lines.append(f"  Nearest: {fib.get('nearest_level', '')} → {fmt_price(fib.get('nearest_price', 0))} ({fib.get('proximity_pct', 0)}%){gz}")
            lines.append("")

        # ── Section: SMC (OB + FVG) ─────────────────────
        lines.append("🧱 *Smart Money Concepts*")
        ob_lines = _fmt_ob_section(ob)
        fvg_lines = _fmt_fvg_section(fvg)
        if ob_lines:
            lines.extend(ob_lines)
        else:
            lines.append("  No significant Order Blocks.")
        if fvg_lines:
            lines.extend(fvg_lines)
        else:
            lines.append("  No open FVGs.")

        # Liquidity
        bl = liq.get("nearest_buy_liq")
        sl_liq = liq.get("nearest_sell_liq")
        if bl or sl_liq:
            pool_parts = []
            if bl: pool_parts.append(f"↑{fmt_price(bl)}")
            if sl_liq: pool_parts.append(f"↓{fmt_price(sl_liq)}")
            lines.append(f"  💧 Liquidity: {' · '.join(pool_parts)}")
        hunts = liq.get("stop_hunts", [])
        for h in hunts[-2:]:
            lines.append(f"  ⚡ {h['type']} @ {fmt_price(h['price'])}")
        lines.append("")

        # ── Section: Indicators ─────────────────────────
        lines.append("📈 *Technical Indicators*")
        rsi = ind["rsi"]
        macd = ind["macd"]
        ema = ind["ema"]
        vol = ind["volume"]
        lines.append(f"  RSI: {rsi['value']} · {rsi['zone']} · {rsi['direction']}")
        lines.append(f"  MACD: {macd['momentum']} · Hist {macd['histogram_trend']}")
        if macd["crossover"] != "None":
            lines.append(f"   ↳ {macd['crossover']}")
        lines.append(f"  EMA: {ema['trend'].split('(')[0].strip()}")
        if ema["cross"] != "None":
            lines.append(f"   ↳ {ema['cross']}")
        if stoch:
            lines.append(f"  Stoch: %K={stoch.get('k', 0)} %D={stoch.get('d', 0)} · {stoch.get('zone', '')}")
            if stoch.get("cross") != "None":
                lines.append(f"   ↳ {stoch['cross']}")
        lines.append(f"  Volume: {vol['trend'].split('(')[0].strip()}")
        if "Spike" in vol.get("spike", ""):
            lines.append(f"   ↳ {vol['spike']}")
        lines.append(f"  ATR: {fmt_price(atr.get('atr', 0))} ({atr.get('atr_pct', 0)}%) · {atr.get('volatility', '')}")
        if bb:
            sq = bb.get("squeeze", "")
            if sq != "No squeeze":
                lines.append(f"  BB: {sq}")
            lines.append(f"  BB Position: {bb.get('position', '')}")
        lines.append("")

        # ── Section: Signals & Divergences ───────────────
        signals = []
        for p in pats:
            e = "🟢" if p["type"] == "bullish" else "🔴" if p["type"] == "bearish" else "⚪"
            signals.append(f"{e} {p['pattern']}")
        all_divs = (
            div.get("rsi", {}).get("divergences", []) +
            div.get("macd", {}).get("divergences", [])
        )
        for d in all_divs:
            signals.append(f"🔀 {d['type']} [{d['indicator']}]")
        if signals:
            lines.append("🕯 *Patterns & Divergences*")
            for s in signals:
                lines.append(f"  {s}")
            lines.append("")

        # ── Section: Signal Quality ─────────────────────
        lines.append("🏆 *Signal Quality Assessment*")
        lines.append(f"  Grade: {ge} *{grade}* · Confidence: *{conf_pct}%*")
        lines.append(f"  Bullish Factors: {conf.get('bullish_signals', 0)} · Bearish: {conf.get('bearish_signals', 0)}")
        # Top factors
        for f in grade_d.get("factors", [])[:5]:
            lines.append(f"  {f}")
        lines.append("")

        # ── Section: Trade Setup ─────────────────────────
        if setup:
            verdict = setup.get("verdict", "")
            pos = setup.get("position", {})
            lines.append("🎯 *Trade Verdict*")
            lines.append(f"  {verdict}")
            lines.append(f"  _{setup.get('verdict_detail', '')}_")

            if setup.get("tradeable") and pos and "error" not in pos:
                dir_emoji = "🟢 LONG" if pos.get("direction") == "BUY" else "🔴 SHORT"
                lines.append(f"  {dir_emoji}")
                lines.append(f"  Entry: `{pos.get('entry', '')}`")
                lines.append(f"  SL:    `{pos.get('sl', '')}`  ({pos.get('sl_distance_pct', 0)}%)")
                lines.append(f"  TP1:   `{pos.get('tp1', '')}`")
                lines.append(f"  TP2:   `{pos.get('tp2', '')}`")
                lines.append(f"  R:R:   *{pos.get('rr_ratio', 0)}x* {pos.get('rr_verdict', '')}")
                lines.append(f"  Size:  ${pos.get('position_size_usd', 0):,.2f} · Lev: {pos.get('leverage', 1)}x")
            elif setup.get("fail_reasons"):
                for r in setup.get("fail_reasons", []):
                    lines.append(f"  ❌ {r}")
            lines.append("")

            # Quality checks grid
            qc = setup.get("quality_checks", {})
            if qc:
                checks = []
                checks.append("✅" if qc.get("confluence_pass") else "❌")
                checks.append("✅" if qc.get("grade_pass") else "❌")
                checks.append("✅" if qc.get("confidence_pass") else "❌")
                checks.append("✅" if qc.get("rr_pass") else "❌")
                checks.append("✅" if qc.get("volume_pass") else "❌")
                checks.append("✅" if qc.get("regime_pass") else "❌")
                labels = ["Conf", "Grade", "Cnfd", "R:R", "Vol", "Rgme"]
                check_str = "  ".join(f"{c}{l}" for c, l in zip(checks, labels))
                lines.append(f"  Quality: `{check_str}`")

        lines.append("")
        lines.append("═" * 30)
        lines.append("")

    lines.append("_Report generated by Crypto Market Analyst Bot_")
    return "\n".join(lines)
