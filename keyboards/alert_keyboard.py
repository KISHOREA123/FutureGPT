"""
keyboards/alert_keyboard.py — Keyboards for the price alert feature.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.alert_store import Alert


def alert_list_keyboard(alerts: list[Alert]) -> InlineKeyboardMarkup:
    """Shown under /listalerts when the user has active alerts."""
    b = InlineKeyboardBuilder()

    for alert in alerts:
        b.button(
            text=f"🗑 #{alert.alert_id} {alert.symbol} ${alert.target:,.0f}",
            callback_data=f"alert:del:{alert.alert_id}",
        )
    b.adjust(2)

    if len(alerts) > 1:
        b.row(InlineKeyboardButton(
            text="🗑 Delete All Alerts",
            callback_data="alert:delall",
        ))

    b.row(
        InlineKeyboardButton(text="➕ Set New Alert", callback_data="alert:howto"),
        InlineKeyboardButton(text="🏠 Menu",          callback_data="action:menu"),
    )
    return b.as_markup()


def alert_set_confirm_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """Shown after an alert is successfully created."""
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📋 My Alerts",       callback_data="alert:list"),
        InlineKeyboardButton(text=f"📊 {symbol} Price", callback_data=f"price:{symbol}"),
        InlineKeyboardButton(text="🏠 Menu",             callback_data="action:menu"),
    )
    return b.as_markup()


def alert_nav_keyboard() -> InlineKeyboardMarkup:
    """Minimal nav shown after a delete/clear action."""
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📋 My Alerts", callback_data="alert:list"),
        InlineKeyboardButton(text="➕ Set Alert",  callback_data="alert:howto"),
        InlineKeyboardButton(text="🏠 Menu",       callback_data="action:menu"),
    )
    return b.as_markup()


def alert_delall_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation dialog before deleting all alerts."""
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Yes, delete all", callback_data="alert:delall:confirm"),
        InlineKeyboardButton(text="❌ Cancel",           callback_data="alert:list"),
    )
    return b.as_markup()


def alert_empty_keyboard() -> InlineKeyboardMarkup:
    """Shown when /listalerts finds no active alerts."""
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="➕ Set Alert", callback_data="alert:howto"),
        InlineKeyboardButton(text="🏠 Menu",      callback_data="action:menu"),
    )
    return b.as_markup()

