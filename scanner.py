"""
Multi-coin scanner: runs analysis on a list of coins and ranks by confluence score.
Used by /scan command.
"""
import concurrent.futures
from analyzer import run_full_analysis


# Default scan list — top coins by volume
DEFAULT_SCAN_LIST = [
    "BTC", "ETH", "BNB", "SOL", "XRP",
    "DOGE", "ADA", "AVAX", "DOT", "LINK",
    "MATIC", "UNI", "ATOM", "LTC", "FIL",
    "APT", "ARB", "OP", "INJ", "SUI",
]


def scan_single(symbol: str) -> dict | None:
    """Run analysis for one symbol and return summary with confluence score."""
    try:
        results = run_full_analysis(symbol)
        # Aggregate confluence across timeframes
        scores = []
        tf_biases = {}
        for tf, data in results.items():
            if "error" in data:
                continue
            conf = data.get("confluence", {})
            score = conf.get("score", 0)
            bias = conf.get("bias", "N/A")
            scores.append(score)
            tf_biases[tf] = {"score": score, "bias": bias}

        if not scores:
            return None

        avg_score = round(sum(scores) / len(scores), 1)
        # Get price from first valid timeframe
        price = None
        for tf, data in results.items():
            if "error" not in data:
                price = data["current_price"]
                break

        return {
            "symbol": symbol,
            "price": price,
            "avg_score": avg_score,
            "tf_biases": tf_biases,
            "raw_results": results,
        }
    except Exception as e:
        return None


def run_scan(coins: list = None, top_n: int = 10) -> dict:
    """
    Scan multiple coins in parallel, rank by confluence score.
    Returns top bullish and bearish setups.
    """
    if not coins:
        coins = DEFAULT_SCAN_LIST

    scan_results = []

    # Use thread pool for parallel fetching
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_to_coin = {executor.submit(scan_single, c): c for c in coins}
        for future in concurrent.futures.as_completed(future_to_coin):
            result = future.result()
            if result:
                scan_results.append(result)

    # Sort by avg confluence score
    scan_results.sort(key=lambda x: x["avg_score"], reverse=True)

    top_bullish = [r for r in scan_results if r["avg_score"] > 0][:top_n // 2]
    top_bearish = [r for r in sorted(scan_results, key=lambda x: x["avg_score"])
                   if r["avg_score"] < 0][:top_n // 2]
    neutral = [r for r in scan_results if r["avg_score"] == 0]

    return {
        "scanned": len(scan_results),
        "top_bullish": top_bullish,
        "top_bearish": top_bearish,
        "neutral": neutral,
        "all_sorted": scan_results,
    }
