"""
Correlation Filter
Computes asset return correlations to flag redundant signals
and assess portfolio diversification risk.
"""
import numpy as np
import pandas as pd
import logging
from config import CORRELATION_THRESHOLD

logger = logging.getLogger(__name__)


def compute_correlation_matrix(price_data: dict, period: int = 30) -> dict:
    """
    Compute Pearson correlation matrix from close price returns.

    Args:
        price_data: dict of {symbol: DataFrame with 'close' column}
        period: number of periods for returns

    Returns:
        dict with correlation matrix and analysis
    """
    if len(price_data) < 2:
        return {"matrix": {}, "pairs": [], "diversification_score": 100}

    # Build returns DataFrame
    returns = {}
    for symbol, df in price_data.items():
        if df is not None and not df.empty and len(df) >= period:
            returns[symbol] = df["close"].pct_change().dropna().tail(period)

    if len(returns) < 2:
        return {"matrix": {}, "pairs": [], "diversification_score": 100}

    # Align all return series
    returns_df = pd.DataFrame(returns)
    returns_df = returns_df.dropna(axis=1, how="all").dropna()

    if returns_df.shape[1] < 2 or len(returns_df) < 10:
        return {"matrix": {}, "pairs": [], "diversification_score": 100}

    # Compute correlation matrix
    corr_matrix = returns_df.corr()

    # Find highly-correlated pairs
    high_corr_pairs = []
    symbols = corr_matrix.columns.tolist()
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            corr = corr_matrix.iloc[i, j]
            if not pd.isna(corr) and abs(corr) >= CORRELATION_THRESHOLD:
                high_corr_pairs.append({
                    "pair": f"{symbols[i]} / {symbols[j]}",
                    "correlation": round(corr, 3),
                    "warning": "⚠️ Highly correlated" if corr > 0 else "⚠️ Inversely correlated",
                })

    # Diversification score (100 = fully diversified, 0 = all identical)
    avg_abs_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)]
    avg_abs_corr = np.abs(avg_abs_corr[~np.isnan(avg_abs_corr)])
    if len(avg_abs_corr) > 0:
        diversification_score = round((1 - avg_abs_corr.mean()) * 100, 1)
    else:
        diversification_score = 100

    return {
        "matrix": {
            s: {s2: round(corr_matrix.loc[s, s2], 3) for s2 in symbols}
            for s in symbols
        },
        "pairs": high_corr_pairs,
        "diversification_score": diversification_score,
        "symbols_analyzed": symbols,
    }


def filter_correlated_signals(signals: list, price_data: dict) -> list:
    """
    Given a list of signals with symbols, flag those that are
    highly correlated and in the same direction (redundant exposure).

    Args:
        signals: list of dicts with 'symbol' and 'direction' keys
        price_data: dict of {symbol: DataFrame}

    Returns:
        Annotated signals list with 'correlation_warning' flag
    """
    if len(signals) < 2:
        return signals

    corr_result = compute_correlation_matrix(price_data)
    corr_matrix = corr_result.get("matrix", {})

    annotated = []
    for sig in signals:
        sym = sig.get("symbol", "")
        direction = sig.get("direction", "")
        warnings = []

        for other_sig in signals:
            other_sym = other_sig.get("symbol", "")
            other_dir = other_sig.get("direction", "")

            if sym == other_sym:
                continue

            corr_val = corr_matrix.get(sym, {}).get(other_sym, 0)
            if abs(corr_val) >= CORRELATION_THRESHOLD:
                if (corr_val > 0 and direction == other_dir):
                    warnings.append(
                        f"⚠️ Correlated with {other_sym} ({corr_val:.2f}) — same direction = redundant risk"
                    )
                elif (corr_val < 0 and direction != other_dir):
                    warnings.append(
                        f"⚠️ Inversely correlated with {other_sym} ({corr_val:.2f}) — opposing directions = hedge"
                    )

        sig_copy = sig.copy()
        sig_copy["correlation_warnings"] = warnings
        sig_copy["is_redundant"] = len(warnings) > 0
        annotated.append(sig_copy)

    return annotated
