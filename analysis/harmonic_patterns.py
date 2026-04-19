"""
Harmonic Pattern Detector — XABCD Pattern Recognition
Detects 6 harmonic patterns using Fibonacci ratio validation:
  Gartley, Butterfly, Bat, Crab, Shark, Cypher
"""
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema


# ── Fibonacci ratio tolerance ────────────────────────────────
FIB_TOLERANCE = 0.10  # 10% tolerance on ratios


# ── Pattern definitions (ideal Fibonacci ratios) ─────────────
HARMONIC_PATTERNS = {
    "Gartley": {
        "XA_to_AB": (0.618, 0.618),
        "AB_to_BC": (0.382, 0.886),
        "XA_to_AD": (0.786, 0.786),
        "emoji": "🦋",
        "reliability": "high",
    },
    "Butterfly": {
        "XA_to_AB": (0.786, 0.786),
        "AB_to_BC": (0.382, 0.886),
        "XA_to_AD": (1.27, 1.618),
        "emoji": "🦋",
        "reliability": "high",
    },
    "Bat": {
        "XA_to_AB": (0.382, 0.50),
        "AB_to_BC": (0.382, 0.886),
        "XA_to_AD": (0.886, 0.886),
        "emoji": "🦇",
        "reliability": "high",
    },
    "Crab": {
        "XA_to_AB": (0.382, 0.618),
        "AB_to_BC": (0.382, 0.886),
        "XA_to_AD": (1.618, 1.618),
        "emoji": "🦀",
        "reliability": "very_high",
    },
    "Shark": {
        "XA_to_AB": (0.446, 0.618),
        "AB_to_BC": (1.13, 1.618),
        "XA_to_AD": (0.886, 1.13),
        "emoji": "🦈",
        "reliability": "moderate",
    },
    "Cypher": {
        "XA_to_AB": (0.382, 0.618),
        "AB_to_BC": (1.13, 1.414),
        "XA_to_AD": (0.786, 0.786),
        "emoji": "🔷",
        "reliability": "moderate",
    },
}


def _find_swing_points(df: pd.DataFrame, order: int = 5) -> tuple:
    """Find swing highs and lows using local extrema detection."""
    highs = argrelextrema(df["high"].values, np.greater_equal, order=order)[0]
    lows = argrelextrema(df["low"].values, np.less_equal, order=order)[0]
    return highs, lows


def _get_swing_sequence(df: pd.DataFrame, highs: np.ndarray, lows: np.ndarray) -> list:
    """Create alternating sequence of swing highs and lows."""
    swings = []
    for idx in highs:
        swings.append({"index": idx, "price": df["high"].iloc[idx], "type": "high"})
    for idx in lows:
        swings.append({"index": idx, "price": df["low"].iloc[idx], "type": "low"})
    swings.sort(key=lambda x: x["index"])

    # Remove consecutive same-type swings (keep most extreme)
    filtered = []
    for s in swings:
        if not filtered or filtered[-1]["type"] != s["type"]:
            filtered.append(s)
        else:
            if s["type"] == "high" and s["price"] > filtered[-1]["price"]:
                filtered[-1] = s
            elif s["type"] == "low" and s["price"] < filtered[-1]["price"]:
                filtered[-1] = s
    return filtered


def _check_ratio(actual: float, expected_min: float, expected_max: float) -> bool:
    """Check if a ratio falls within expected range + tolerance."""
    lower = min(expected_min, expected_max) * (1 - FIB_TOLERANCE)
    upper = max(expected_min, expected_max) * (1 + FIB_TOLERANCE)
    return lower <= actual <= upper


def _validate_pattern(
    x_price: float, a_price: float, b_price: float,
    c_price: float, d_price: float, pattern_name: str
) -> bool:
    """Validate XABCD points against a specific pattern's Fibonacci ratios."""
    pattern = HARMONIC_PATTERNS.get(pattern_name)
    if not pattern:
        return False

    xa = abs(a_price - x_price)
    ab = abs(b_price - a_price)
    bc = abs(c_price - b_price)
    ad = abs(d_price - a_price)

    if xa == 0:
        return False

    # AB/XA ratio
    ab_xa = ab / xa
    if not _check_ratio(ab_xa, *pattern["XA_to_AB"]):
        return False

    # BC/AB ratio
    if ab > 0:
        bc_ab = bc / ab
        if not _check_ratio(bc_ab, *pattern["AB_to_BC"]):
            return False

    # AD/XA ratio (D completion point)
    ad_xa = ad / xa
    if not _check_ratio(ad_xa, *pattern["XA_to_AD"]):
        return False

    return True


def detect_harmonic_patterns(df: pd.DataFrame) -> dict:
    """
    Detect XABCD harmonic patterns in price data.

    Returns:
        dict with 'patterns' list and summary info
    """
    if len(df) < 30:
        return {"patterns": [], "count": 0, "bias": "neutral"}

    detected = []

    # Try different swing detection granularities
    for order in [3, 5, 8]:
        try:
            highs, lows = _find_swing_points(df, order=order)
            swings = _get_swing_sequence(df, highs, lows)

            if len(swings) < 5:
                continue

            # Check last several 5-point combinations
            for i in range(max(0, len(swings) - 10), len(swings) - 4):
                x = swings[i]
                a = swings[i + 1]
                b = swings[i + 2]
                c = swings[i + 3]
                d = swings[i + 4]

                # Determine if bullish or bearish pattern
                if x["type"] == "low" and a["type"] == "high":
                    direction = "bullish"
                elif x["type"] == "high" and a["type"] == "low":
                    direction = "bearish"
                else:
                    continue

                for name, spec in HARMONIC_PATTERNS.items():
                    if _validate_pattern(
                        x["price"], a["price"], b["price"],
                        c["price"], d["price"], name
                    ):
                        # Calculate entry, SL, TP levels
                        xa = abs(a["price"] - x["price"])

                        if direction == "bullish":
                            entry = d["price"]
                            sl = d["price"] - (xa * 0.15)
                            tp1 = d["price"] + (xa * 0.382)
                            tp2 = d["price"] + (xa * 0.618)
                            tp3 = d["price"] + (xa * 1.0)
                        else:
                            entry = d["price"]
                            sl = d["price"] + (xa * 0.15)
                            tp1 = d["price"] - (xa * 0.382)
                            tp2 = d["price"] - (xa * 0.618)
                            tp3 = d["price"] - (xa * 1.0)

                        pattern_data = {
                            "name": name,
                            "emoji": spec["emoji"],
                            "direction": direction,
                            "reliability": spec["reliability"],
                            "points": {
                                "X": round(x["price"], 6),
                                "A": round(a["price"], 6),
                                "B": round(b["price"], 6),
                                "C": round(c["price"], 6),
                                "D": round(d["price"], 6),
                            },
                            "entry": round(entry, 6),
                            "sl": round(sl, 6),
                            "tp1": round(tp1, 6),
                            "tp2": round(tp2, 6),
                            "tp3": round(tp3, 6),
                            "completion_index": d["index"],
                        }

                        # Avoid duplicates
                        is_dupe = any(
                            p["name"] == name and p["direction"] == direction
                            and abs(p["points"]["D"] - d["price"]) / d["price"] < 0.01
                            for p in detected
                        )
                        if not is_dupe:
                            detected.append(pattern_data)

        except Exception:
            continue

    # Determine overall bias
    bullish = sum(1 for p in detected if p["direction"] == "bullish")
    bearish = sum(1 for p in detected if p["direction"] == "bearish")
    if bullish > bearish:
        bias = "bullish"
    elif bearish > bullish:
        bias = "bearish"
    else:
        bias = "neutral"

    return {
        "patterns": detected[:5],  # Limit to top 5 most recent
        "count": len(detected),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "bias": bias,
    }
