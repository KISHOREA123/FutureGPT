import json
import os
import asyncio
from datetime import datetime

WATCHLIST_FILE = "watchlist.json"


def load_watchlist() -> dict:
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    return {}


def save_watchlist(wl: dict):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(wl, f, indent=2)


def add_to_watchlist(symbol: str) -> str:
    symbol = symbol.upper().replace("/USDT", "").strip()
    wl = load_watchlist()
    if symbol in wl:
        return f"⚠️ {symbol} is already in your watchlist."
    wl[symbol] = {"added": datetime.now().isoformat(), "last_alert": None}
    save_watchlist(wl)
    return f"✅ *{symbol}* added to watchlist! I'll alert you on pattern detection."


def remove_from_watchlist(symbol: str) -> str:
    symbol = symbol.upper().replace("/USDT", "").strip()
    wl = load_watchlist()
    if symbol not in wl:
        return f"⚠️ {symbol} is not in your watchlist."
    del wl[symbol]
    save_watchlist(wl)
    return f"🗑 *{symbol}* removed from watchlist."


def list_watchlist() -> str:
    wl = load_watchlist()
    if not wl:
        return "📋 Your watchlist is empty. Use /alert add <coin> to add coins."
    lines = ["📋 *Watchlist:*\n"]
    for sym, info in wl.items():
        last = info.get("last_alert") or "Never"
        lines.append(f"• {sym}/USDT (Last alert: {last})")
    return "\n".join(lines)


def get_watchlist_symbols() -> list:
    return list(load_watchlist().keys())


def update_last_alert(symbol: str):
    wl = load_watchlist()
    if symbol in wl:
        wl[symbol]["last_alert"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_watchlist(wl)
