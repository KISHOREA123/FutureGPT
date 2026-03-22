"""
keyboards/news_keyboard.py — Keyboards for the news feature.

Screens:
  • news_dashboard_keyboard()  — general news with coin-filter quick-picks
  • news_coin_keyboard(symbol) — coin-specific news with active marker + nav
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Coins available as news filters (top 8)
NEWS_COINS: list[tuple[str, str]] = [
    ("BTC",  "BTC"),
    ("ETH",  "ETH"),
    ("SOL",  "SOL"),
    ("XRP",  "XRP"),
    ("BNB",  "BNB"),
    ("ADA",  "ADA"),
    ("DOGE", "DOGE"),
    ("AVAX", "AVAX"),
]


def news_dashboard_keyboard() -> InlineKeyboardMarkup:
    """
    General news screen.

    Layout:
      [BTC]  [ETH]  [SOL]  [XRP]
      [BNB]  [ADA]  [DOGE] [AVAX]
      [🔄 Refresh]  [📊 Price]  [📈 Signal]
      [💬 Ask AI]   [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    for symbol, label in NEWS_COINS:
        b.button(text=label, callback_data=f"news:{symbol}")
    b.adjust(4)

    b.row(
        InlineKeyboardButton(text="🔄 Refresh",  callback_data="action:news"),
        InlineKeyboardButton(text="📊 Price",    callback_data="action:price"),
        InlineKeyboardButton(text="📈 Signal",   callback_data="action:signal"),
    )
    b.row(
        InlineKeyboardButton(text="💬 Ask AI",   callback_data="action:askai"),
        InlineKeyboardButton(text="🏠 Menu",     callback_data="action:menu"),
    )
    return b.as_markup()


def news_coin_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Coin-specific news screen.
    Active coin gets ✅ prefix.

    Layout:
      [✅ BTC]  [ETH]  [SOL]  [XRP]    ← active coin highlighted
      [BNB]     [ADA]  [DOGE] [AVAX]
      [🔄 Refresh]  [📰 All News]  [📊 Price]
      [📈 Signal]   [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    for sym, label in NEWS_COINS:
        prefix = "✅ " if sym == symbol else ""
        b.button(text=f"{prefix}{label}", callback_data=f"news:{sym}")
    b.adjust(4)

    b.row(
        InlineKeyboardButton(text="🔄 Refresh",    callback_data=f"news:{symbol}"),
        InlineKeyboardButton(text="📰 All News",   callback_data="action:news"),
        InlineKeyboardButton(text="📊 Price",      callback_data=f"price:{symbol}"),
    )
    b.row(
        InlineKeyboardButton(text="📈 Signal",     callback_data=f"signal:{symbol}"),
        InlineKeyboardButton(text="🏠 Menu",       callback_data="action:menu"),
    )
    return b.as_markup()
