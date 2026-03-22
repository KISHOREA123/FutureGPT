"""
keyboards/kb.py — Centralised keyboard factory (single source of truth).

Design principles:
  • Every screen has ONE keyboard definition here.
  • Keyboards are composed from reusable row builders.
  • callback_data scheme:
        action:<name>          — top-level navigation
        price:<SYMBOL>         — price detail for a coin
        signal:<SYMBOL>        — signal detail for a coin
        coin:<SYMBOL>:<mode>   — coin selector → routes to price or signal
  • Every detail screen gets the universal action bar:
        [🔄 Refresh] [📊 Price] [📈 Signal]
  • Every screen gets a coin selector strip:
        [BTC] [ETH] [SOL] [XRP]  (with optional active marker)
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ── Coin catalogue ─────────────────────────────────────────────────────────────

# Primary 4 coins shown in the selector strip everywhere
PRIMARY_COINS: list[tuple[str, str]] = [
    ("BTC",  "BTC"),
    ("ETH",  "ETH"),
    ("SOL",  "SOL"),
    ("XRP",  "XRP"),
]

# Extended coins shown on dashboard screens
EXTENDED_COINS: list[tuple[str, str]] = PRIMARY_COINS + [
    ("BNB",  "BNB"),
    ("ADA",  "ADA"),
    ("DOGE", "DOGE"),
    ("AVAX", "AVAX"),
]


# ── Row builders (private) ─────────────────────────────────────────────────────

def _action_bar(refresh_data: str) -> list[InlineKeyboardButton]:
    """Universal [🔄 Refresh] [📊 Price] [📈 Signal] action bar."""
    return [
        InlineKeyboardButton(text="🔄 Refresh",  callback_data=refresh_data),
        InlineKeyboardButton(text="📊 Price",    callback_data="action:price"),
        InlineKeyboardButton(text="📈 Signal",   callback_data="action:signal"),
    ]


def _coin_selector(mode: str, active: str = "") -> list[list[InlineKeyboardButton]]:
    """
    Primary coin strip.
    Active coin gets a ✅ prefix so users see which they selected.

    Args:
        mode:   "price" or "signal" — determines callback_data prefix
        active: currently-shown symbol (empty = none highlighted)
    """
    buttons = []
    for symbol, label in PRIMARY_COINS:
        prefix = "✅ " if symbol == active else ""
        buttons.append(
            InlineKeyboardButton(
                text=f"{prefix}{label}",
                callback_data=f"{mode}:{symbol}",
            )
        )
    return [buttons]   # one row of 4


def _nav_row(include_menu: bool = True, include_news: bool = False) -> list[InlineKeyboardButton]:
    """Bottom navigation row."""
    buttons = []
    if include_news:
        buttons.append(InlineKeyboardButton(text="📰 News",   callback_data="action:news"))
    buttons.append(InlineKeyboardButton(text="💬 Ask AI",     callback_data="action:askai"))
    if include_menu:
        buttons.append(InlineKeyboardButton(text="🏠 Menu",   callback_data="action:menu"))
    return buttons


# ── Public keyboard factories ──────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Home screen — feature grid + analyze + alert button + coin selector.

    Layout:
      [📊 Price]    [📈 Signal]
      [📰 News]     [💬 Ask AI]
      [🔍 Analyze]  [🔔 Alerts]
      [BTC] [ETH] [SOL] [XRP]
    """
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📊 Price",    callback_data="action:price"),
        InlineKeyboardButton(text="📈 Signal",   callback_data="action:signal"),
    )
    b.row(
        InlineKeyboardButton(text="📰 News",     callback_data="action:news"),
        InlineKeyboardButton(text="💬 Ask AI",   callback_data="action:askai"),
    )
    b.row(
        InlineKeyboardButton(text="🔍 Analyze",  callback_data="action:analyze"),
        InlineKeyboardButton(text="🔔 Alerts",   callback_data="alert:list"),
    )
    b.row(
        InlineKeyboardButton(text="📰 Daily Digest", callback_data="digest:status"),
        InlineKeyboardButton(text="🎓 Tour",          callback_data="onboard:1"),
    )
    for row in _coin_selector("price"):
        b.row(*row)
    return b.as_markup()


def price_dashboard_keyboard() -> InlineKeyboardMarkup:
    """
    Price overview screen.

    Layout:
      [BTC] [ETH] [SOL] [XRP]   ← tap to drill in
      [BNB] [ADA] [DOGE] [AVAX]
      [🔄 Refresh] [📊 Price] [📈 Signal]
      [💬 Ask AI]  [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    # Extended coin grid
    for symbol, label in EXTENDED_COINS:
        b.button(text=label, callback_data=f"price:{symbol}")
    b.adjust(4)

    b.row(*_action_bar("action:price"))
    b.row(*_nav_row(include_menu=True))
    return b.as_markup()


def price_detail_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Single-coin price detail card.

    Layout:
      [BTC] [ETH] [SOL] [XRP]   ← active coin highlighted
      [🔄 Refresh] [📊 Price] [📈 Signal]
      [📈 Get Signal]          [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    for row in _coin_selector("price", active=symbol):
        b.row(*row)

    b.row(*_action_bar(f"price:{symbol}"))
    b.row(
        InlineKeyboardButton(text="📈 Get Signal", callback_data=f"signal:{symbol}"),
        InlineKeyboardButton(text="🏠 Menu",        callback_data="action:menu"),
    )
    return b.as_markup()


def signal_dashboard_keyboard() -> InlineKeyboardMarkup:
    """
    Signal overview screen.

    Layout:
      [BTC] [ETH] [SOL] [XRP]
      [BNB] [ADA] [DOGE] [AVAX]
      [🔄 Refresh] [📊 Price] [📈 Signal]
      [💬 Ask AI]  [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    for symbol, label in EXTENDED_COINS:
        b.button(text=label, callback_data=f"signal:{symbol}")
    b.adjust(4)

    b.row(*_action_bar("action:signal"))
    b.row(*_nav_row(include_menu=True))
    return b.as_markup()


def signal_detail_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Single-coin signal detail card.

    Layout:
      [BTC] [ETH] [SOL] [XRP]   ← active coin highlighted
      [🔄 Refresh] [📊 Price] [📈 Signal]
      [💰 Get Price]           [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    for row in _coin_selector("signal", active=symbol):
        b.row(*row)

    b.row(*_action_bar(f"signal:{symbol}"))
    b.row(
        InlineKeyboardButton(text="💰 Get Price",  callback_data=f"price:{symbol}"),
        InlineKeyboardButton(text="🏠 Menu",        callback_data="action:menu"),
    )
    return b.as_markup()


def news_keyboard() -> InlineKeyboardMarkup:
    """
    News screen.

    Layout:
      [🔄 Refresh] [📊 Price] [📈 Signal]
      [💬 Ask AI]  [🏠 Menu]
    """
    b = InlineKeyboardBuilder()
    b.row(*_action_bar("action:news"))
    b.row(*_nav_row(include_menu=True))
    return b.as_markup()


def askai_keyboard() -> InlineKeyboardMarkup:
    """
    Ask AI prompt screen — no coin selector, just navigation.

    Layout:
      [📊 Price] [📈 Signal] [🏠 Menu]
    """
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📊 Price",  callback_data="action:price"),
        InlineKeyboardButton(text="📈 Signal", callback_data="action:signal"),
        InlineKeyboardButton(text="🏠 Menu",   callback_data="action:menu"),
    )
    return b.as_markup()


def askai_result_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard shown after AI answers — coin strip + action bar.

    Layout:
      [BTC] [ETH] [SOL] [XRP]
      [🔄 Ask Again] [📊 Price] [📈 Signal]
      [🏠 Menu]
    """
    b = InlineKeyboardBuilder()
    for row in _coin_selector("price"):
        b.row(*row)
    b.row(
        InlineKeyboardButton(text="🔄 Ask Again", callback_data="action:askai"),
        InlineKeyboardButton(text="📊 Price",      callback_data="action:price"),
        InlineKeyboardButton(text="📈 Signal",     callback_data="action:signal"),
    )
    b.row(InlineKeyboardButton(text="🏠 Menu", callback_data="action:menu"))
    return b.as_markup()


def error_keyboard(retry_data: str) -> InlineKeyboardMarkup:
    """
    Shown when a fetch fails.

    Layout:
      [🔄 Try Again] [🏠 Menu]
    """
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🔄 Try Again", callback_data=retry_data),
        InlineKeyboardButton(text="🏠 Menu",       callback_data="action:menu"),
    )
    return b.as_markup()


# ── Backwards compatibility aliases ───────────────────────────────────────────
# Old names referenced by handlers — redirect to new factories.

def back_keyboard() -> InlineKeyboardMarkup:
    """Alias kept for any remaining references — returns news keyboard."""
    return news_keyboard()


def price_coins_keyboard() -> InlineKeyboardMarkup:
    return price_dashboard_keyboard()


def signal_coins_keyboard() -> InlineKeyboardMarkup:
    return signal_dashboard_keyboard()