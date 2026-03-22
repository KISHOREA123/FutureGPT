"""
keyboards/analyze_keyboard.py — Keyboards for the Analyze / Search feature.

Screens:
  1. analyze_search_keyboard()         — Entry: 8 popular coins + More + Gainers/Losers
  2. analyze_page_keyboard(page)       — Paginated A-Z coin grid (10 coins/page, 5 per row)
  3. analyze_result_keyboard(sym)      — After analysis: Price | Signal | News | Search Again
  4. analyze_movers_keyboard()         — After gainers/losers card
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ── Full coin catalogue (A-Z) ─────────────────────────────────────────────────

QUICK_COINS: list[str] = ["BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "TON", "ADA"]

ALL_COINS: list[str] = sorted([
    "ADA", "ALGO", "APT", "ARB", "ATOM", "AVAX", "AXS",
    "BNB", "BONK", "BRETT", "BTC",
    "CAKE", "CHZ", "CRV",
    "DASH", "DOGE", "DOT",
    "EGLD", "ENS", "EOS", "ETC", "ETH",
    "FET", "FIL", "FLOKI",
    "GALA", "GRT",
    "HBAR",
    "ICP", "IMX", "INJ",
    "KAS",
    "LDO", "LINK", "LTC",
    "MANA", "MKR",
    "NEAR", "NOT",
    "OP",
    "PEPE", "POL",
    "RENDER", "RUNE",
    "SAND", "SHIB", "SNX", "SOL", "SUI",
    "THETA", "TON", "TRX",
    "UNI",
    "VET",
    "WIF",
    "XLM", "XMR", "XRP", "XTZ",
    "ZEC",
])

COINS_PER_PAGE = 25     # 25 coins per page → 5 rows of 5
COLS           = 5


def _total_pages() -> int:
    import math
    return math.ceil(len(ALL_COINS) / COINS_PER_PAGE)


# ── Keyboards ─────────────────────────────────────────────────────────────────

def analyze_search_keyboard() -> InlineKeyboardMarkup:
    """
    Entry screen — 8 quick coins + movers + more.

    Layout:
      [BTC]  [ETH]  [BNB]  [SOL]
      [XRP]  [DOGE] [TON]  [ADA]
      [🚀 Top Gainers]  [📉 Top Losers]
      [⭐ More Popular Coins]
      [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    for sym in QUICK_COINS:
        b.button(text=sym, callback_data=f"analyze:{sym}")
    b.adjust(4)

    b.row(
        InlineKeyboardButton(text="🚀 Top Gainers", callback_data="analyze:gainers"),
        InlineKeyboardButton(text="📉 Top Losers",  callback_data="analyze:losers"),
    )
    b.row(InlineKeyboardButton(text="⭐ More Popular Coins", callback_data="analyze:page:0"))
    b.row(InlineKeyboardButton(text="🏠 Menu", callback_data="action:menu"))
    return b.as_markup()


def analyze_page_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """
    Paginated coin grid — 25 coins per page, 5 per row.

    Layout:
      [coin] [coin] [coin] [coin] [coin]   × 5 rows
      [⬅️ Prev]  Page N/M  [Next ➡️]
      [🔍 Analyze Any Coin]
      [🚀 Gainers] [📉 Losers] [🏠 Menu]
    """
    total = _total_pages()
    page  = max(0, min(page, total - 1))

    start = page * COINS_PER_PAGE
    coins = ALL_COINS[start: start + COINS_PER_PAGE]

    b = InlineKeyboardBuilder()

    for sym in coins:
        b.button(text=sym, callback_data=f"analyze:{sym}")
    b.adjust(COLS)

    # Pagination row
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"analyze:page:{page - 1}",
        ))
    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {page + 1}/{total}",
        callback_data="noop",   # page indicator — not clickable (no-op)
    ))
    if page < total - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"analyze:page:{page + 1}",
        ))
    b.row(*nav_buttons)

    b.row(InlineKeyboardButton(text="🔍 Analyze Any Coin", callback_data="analyze:search"))
    b.row(
        InlineKeyboardButton(text="🚀 Gainers",  callback_data="analyze:gainers"),
        InlineKeyboardButton(text="📉 Losers",   callback_data="analyze:losers"),
        InlineKeyboardButton(text="🏠 Menu",     callback_data="action:menu"),
    )
    return b.as_markup()


def analyze_movers_keyboard() -> InlineKeyboardMarkup:
    """
    Shown under the Top Movers card.

    Layout:
      [🔄 Refresh]
      [⭐ Coins List]  [🔍 Search]  [🏠 Menu]
    """
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔄 Refresh", callback_data="analyze:movers"))
    b.row(
        InlineKeyboardButton(text="⭐ Coins List", callback_data="analyze:page:0"),
        InlineKeyboardButton(text="🔍 Search",     callback_data="analyze:search"),
        InlineKeyboardButton(text="🏠 Menu",       callback_data="action:menu"),
    )
    return b.as_markup()


def analyze_result_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    After a coin analysis card.

    Layout:
      [💰 Price]   [📈 Signal]
      [📰 News]    [💬 Ask AI]
      [🔍 Search Again]  [🏠 Menu]
    """
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💰 Price",  callback_data=f"price:{symbol}"),
        InlineKeyboardButton(text="📈 Signal", callback_data=f"signal:{symbol}"),
    )
    b.row(
        InlineKeyboardButton(text="📰 News",   callback_data=f"news:{symbol}"),
        InlineKeyboardButton(text="💬 Ask AI", callback_data="action:askai"),
    )
    b.row(
        InlineKeyboardButton(text="🔍 Search Again", callback_data="action:analyze"),
        InlineKeyboardButton(text="🏠 Menu",         callback_data="action:menu"),
    )
    return b.as_markup()


def analyze_fsm_keyboard() -> InlineKeyboardMarkup:
    """Shown while FSM waits for user to type a coin name."""
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="⭐ Popular Coins", callback_data="analyze:page:0"),
        InlineKeyboardButton(text="❌ Cancel",         callback_data="action:analyze"),
    )
    return b.as_markup()