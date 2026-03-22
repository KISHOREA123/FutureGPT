"""
keyboards/signal_keyboard.py — Keyboards for the AI signal feature.

Provides:
  • signal_coins_keyboard()  — quick-pick grid shown after overview
  • signal_detail_keyboard() — refresh + back buttons on a single-coin card
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

SIGNAL_COINS: list[tuple[str, str]] = [
    ("BTC",  "BTC"),
    ("ETH",  "ETH"),
    ("BNB",  "BNB"),
    ("SOL",  "SOL"),
    ("XRP",  "XRP"),
    ("ADA",  "ADA"),
    ("DOGE", "DOGE"),
    ("AVAX", "AVAX"),
]


def signal_coins_keyboard() -> InlineKeyboardMarkup:
    """
    4×2 quick-pick grid below the overview card.
    Each button triggers callback_data="signal:SYMBOL".
    """
    builder = InlineKeyboardBuilder()
    for symbol, label in SIGNAL_COINS:
        builder.button(text=label, callback_data=f"signal:{symbol}")
    builder.adjust(4)
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="action:menu")
    )
    return builder.as_markup()


def signal_detail_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """
    Shown under a single-coin signal card.
    Offers refresh + back-to-overview + back-to-menu.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔄 Refresh Signal",
            callback_data=f"signal:{symbol}",
        ),
        InlineKeyboardButton(
            text="📊 Price",
            callback_data=f"price:{symbol}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="📈 Overview",
            callback_data="action:signal",
        ),
        InlineKeyboardButton(
            text="⬅️ Menu",
            callback_data="action:menu",
        ),
    )
    return builder.as_markup()
