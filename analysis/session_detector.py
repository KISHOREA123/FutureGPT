"""
Trading Session Detector
Detects the active global trading session and provides
session-specific confidence adjustments.
"""
from datetime import datetime, timezone
from config import TRADING_SESSIONS, SESSION_CONFIDENCE_ADJUST


def detect_session() -> dict:
    """
    Detect the current active trading session based on UTC time.

    Sessions:
        Asian:      00:00 - 08:00 UTC
        London:     08:00 - 16:00 UTC
        New York:   13:00 - 22:00 UTC
        Overlap:    13:00 - 16:00 UTC (London + NY)
        Off-hours:  22:00 - 00:00 UTC

    Returns:
        dict with session info and confidence adjustment
    """
    now = datetime.now(timezone.utc)
    hour = now.hour

    active_sessions = []
    session_key = "off_hours"

    # Check London/NY overlap first (highest priority)
    overlap = TRADING_SESSIONS.get("overlap_london_ny", {})
    if overlap.get("start", 99) <= hour < overlap.get("end", 0):
        active_sessions.append("overlap_london_ny")
        session_key = "overlap_london_ny"

    # Check individual sessions
    for name, config in TRADING_SESSIONS.items():
        if name == "overlap_london_ny":
            continue
        start = config.get("start", 99)
        end = config.get("end", 0)
        if start <= hour < end:
            active_sessions.append(name)
            if session_key == "off_hours":
                session_key = name

    # If overlap is active, prioritize it
    if "overlap_london_ny" in active_sessions:
        session_key = "overlap_london_ny"

    # Get session info
    if session_key in TRADING_SESSIONS:
        session_label = TRADING_SESSIONS[session_key]["label"]
    else:
        session_label = "🌙 Off-Hours"

    confidence_adj = SESSION_CONFIDENCE_ADJUST.get(session_key, 0)

    # Session characteristics
    characteristics = {
        "asian": {
            "volatility": "Low to Medium",
            "liquidity": "Low",
            "description": "Range-bound. Accumulation zone. Avoid breakout trades.",
            "best_for": "Range trading, S/R bounces",
        },
        "london": {
            "volatility": "High",
            "liquidity": "High",
            "description": "Major moves begin. Breakouts common. High volume.",
            "best_for": "Breakout trades, trend-following",
        },
        "new_york": {
            "volatility": "High",
            "liquidity": "Very High",
            "description": "Continuation or reversal of London moves. High impact news.",
            "best_for": "Momentum trades, news-driven setups",
        },
        "overlap_london_ny": {
            "volatility": "Very High",
            "liquidity": "Highest",
            "description": "Peak liquidity window. Best time for large moves.",
            "best_for": "All strategies — optimal liquidity",
        },
        "off_hours": {
            "volatility": "Very Low",
            "liquidity": "Very Low",
            "description": "Thin order books. Prone to wicks and stop hunts.",
            "best_for": "Best to avoid trading",
        },
    }

    session_info = characteristics.get(session_key, characteristics["off_hours"])

    return {
        "session": session_key,
        "label": session_label,
        "confidence_adjustment": confidence_adj,
        "active_sessions": active_sessions,
        "utc_hour": hour,
        "utc_time": now.strftime("%H:%M UTC"),
        "volatility": session_info["volatility"],
        "liquidity": session_info["liquidity"],
        "description": session_info["description"],
        "best_for": session_info["best_for"],
    }
