from data_fetcher import fetch_from_both, fetch_ohlcv
from analysis.support_resistance import get_support_resistance
from analysis.market_structure import detect_market_structure
from analysis.candlestick_patterns import detect_patterns
from analysis.indicators import run_indicators, calculate_rsi, calculate_macd
from analysis.liquidity import get_liquidity_zones
from analysis.fibonacci import calculate_fibonacci
from analysis.divergence import detect_rsi_divergence, detect_macd_divergence
from analysis.confluence import calculate_confluence
from analysis.atr_bb import get_atr_analysis, get_bb_analysis
from analysis.order_blocks import detect_order_blocks
from analysis.fvg import detect_fvg
from analysis.htf_bias import get_daily_bias
from analysis.trend_strength import get_trend_strength
from analysis.regime import classify_regime
from analysis.trade_setup import generate_trade_setup
from config import TIMEFRAMES


def run_full_analysis(symbol: str, timeframes: list = None) -> dict:
    """
    Orchestrate full analysis for a symbol across specified timeframes.
    Returns a combined result dict per timeframe, plus HTF daily bias.
    Now includes: trend strength, regime, signal grading, and trade setups.

    Args:
        symbol:     Coin symbol (e.g. 'BTC')
        timeframes: List of timeframes to analyze (e.g. ['1h', '4h']).
                    Defaults to TIMEFRAMES from config if None.
    """
    if timeframes is None:
        timeframes = TIMEFRAMES

    results = {}

    # ── HTF Daily Bias (fetched once, outside TF loop) ──────────
    try:
        df_daily, _ = fetch_from_both(symbol, "1d")
        results["__htf__"] = get_daily_bias(df_daily)
    except Exception as e:
        results["__htf__"] = {"error": str(e)}

    htf_bias = results.get("__htf__", {})

    # ── Per-timeframe analysis ───────────────────────────────────
    for tf in timeframes:
        try:
            df, exchange = fetch_from_both(symbol, tf)
            current_price = float(df["close"].iloc[-1])

            # Core modules
            sr         = get_support_resistance(df, current_price)
            structure  = detect_market_structure(df)
            patterns   = detect_patterns(df)
            indicators = run_indicators(df)
            liquidity  = get_liquidity_zones(df, current_price)
            fib        = calculate_fibonacci(df)

            # Divergence
            rsi_series          = calculate_rsi(df["close"])
            macd_line, _, _hist = calculate_macd(df["close"])
            div_rsi             = detect_rsi_divergence(df, rsi_series)
            div_macd            = detect_macd_divergence(df, macd_line)

            # Volatility
            atr         = get_atr_analysis(df)
            bb          = get_bb_analysis(df)

            # Smart Money Concepts
            order_blocks = detect_order_blocks(df)
            fvg         = detect_fvg(df)

            # ── NEW: Trend Strength ──────────────────────
            trend_data = get_trend_strength(df)

            # ── NEW: Market Regime ───────────────────────
            ema_trend = indicators["ema"]["trend"]
            ema_bias = "bullish" if "Uptrend" in ema_trend or "Bullish" in ema_trend else (
                "bearish" if "Downtrend" in ema_trend or "Bearish" in ema_trend else "mixed"
            )
            regime_data = classify_regime(
                adx_val=trend_data["adx"]["adx"],
                adx_rising=trend_data["adx"]["adx_rising"],
                ema_bias=ema_bias,
                atr_ratio=atr.get("atr_ratio", 1.0),
                bb_squeeze_ratio=bb.get("squeeze_ratio", 1.0),
                trend_label=structure["trend"],
            )

            # ── Enhanced Confluence (now includes OB/FVG/HTF) ──
            confluence = calculate_confluence(
                ms=structure,
                indicators=indicators,
                patterns=patterns,
                liquidity=liquidity,
                fib=fib,
                div_rsi=div_rsi,
                div_macd=div_macd,
                current_price=current_price,
                order_blocks=order_blocks,
                fvg=fvg,
                htf_bias=htf_bias if "error" not in htf_bias else None,
            )

            # ── NEW: Trade Setup (quality gate) ──────────
            trade_setup = generate_trade_setup(
                symbol=symbol.upper(),
                timeframe=tf,
                current_price=current_price,
                confluence=confluence,
                indicators=indicators,
                patterns=patterns,
                div_rsi=div_rsi,
                div_macd=div_macd,
                trend_data=trend_data,
                regime_data=regime_data,
                atr_data=atr,
                ob_data=order_blocks,
                fvg_data=fvg,
                sr_data=sr,
                htf_bias=htf_bias if "error" not in htf_bias else None,
            )

            results[tf] = {
                "exchange":            exchange,
                "symbol":              symbol.upper(),
                "timeframe":           tf,
                "current_price":       current_price,
                "support_resistance":  sr,
                "market_structure":    structure,
                "candlestick_patterns": patterns,
                "indicators":          indicators,
                "liquidity":           liquidity,
                "fibonacci":           fib,
                "divergence":          {"rsi": div_rsi, "macd": div_macd},
                "atr":                 atr,
                "bollinger":           bb,
                "order_blocks":        order_blocks,
                "fvg":                 fvg,
                "confluence":          confluence,
                "trend_strength":      trend_data,
                "regime":              regime_data,
                "trade_setup":         trade_setup,
                "candle_count":        len(df),
            }

        except Exception as e:
            results[tf] = {"error": str(e), "timeframe": tf}

    return results
