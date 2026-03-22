"""
keyboards/price_keyboard.py — Keyboards for the price feature.

Provides:
  • price_coins_keyboard()  — quick-pick grid of popular coins
  • price_back_keyboard()   — back + refresh buttons on a single-coin view
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Coins shown as quick-pick buttons (symbol → display label)
QUICK_COINS: list[tuple[str, str]] = [
    ("BTC",  "BTC"),
    ("ETH",  "ETH"),
    ("BNB",  "BNB"),
    ("SOL",  "SOL"),
    ("XRP",  "XRP"),
    ("ADA",  "ADA"),
    ("DOGE", "DOGE"),
    ("AVAX", "AVAX"),
]


def price_coins_keyboard() -> InlineKeyboardMarkup:
    """
    4×2 grid of popular coins below the dashboard overview.
    Each button triggers callback_data="price:SYMBOL".
    """
    builder = InlineKeyboardBuilder()
    for symbol, label in QUICK_COINS:
        builder.button(text=label, callback_data=f"price:{symbol}")
    builder.adjust(4)   # 4 buttons per row → two rows of 4
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="action:menu")
    )
    return builder.as_markup()


def price_detail_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Keyboard shown under a single-coin price card.
    Offers refresh + back-to-dashboard + back-to-menu.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔄 Refresh",
            callback_data=f"price:{symbol}",
        ),
        InlineKeyboardButton(
            text="📊 Dashboard",
            callback_data="action:price",
        ),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="action:menu")
    )
    return builder.as_markup()
