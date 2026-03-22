"""
keyboards/main_keyboard.py — Reusable inline keyboard factory.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Return the primary 2×2 inline keyboard shown after /start."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Price",  callback_data="action:price"),
        InlineKeyboardButton(text="📈 Signal", callback_data="action:signal"),
    )
    builder.row(
        InlineKeyboardButton(text="📰 News",   callback_data="action:news"),
        InlineKeyboardButton(text="💬 Ask AI", callback_data="action:askai"),
    )

    return builder.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    """Single 'Back' button that returns the user to the main menu."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back to Menu", callback_data="action:menu")
    return builder.as_markup()
