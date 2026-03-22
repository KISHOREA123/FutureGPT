"""
keyboards/__init__.py — Re-exports all keyboards from centralised modules.
"""
from .kb import (
    main_menu_keyboard,
    price_dashboard_keyboard,
    price_detail_keyboard,
    signal_dashboard_keyboard,
    signal_detail_keyboard,
    news_keyboard,
    askai_keyboard,
    askai_result_keyboard,
    error_keyboard,
    back_keyboard,
    price_coins_keyboard,
    signal_coins_keyboard,
    PRIMARY_COINS,
    EXTENDED_COINS,
)
from .chat_keyboard import (
    chat_prompt_keyboard,
    chat_reply_keyboard,
    chat_clear_confirm_keyboard,
)
from .news_keyboard import (
    news_dashboard_keyboard,
    news_coin_keyboard,
)

__all__ = [
    "main_menu_keyboard",
    "price_dashboard_keyboard",
    "price_detail_keyboard",
    "signal_dashboard_keyboard",
    "signal_detail_keyboard",
    "news_keyboard",
    "askai_keyboard",
    "askai_result_keyboard",
    "error_keyboard",
    "back_keyboard",
    "price_coins_keyboard",
    "signal_coins_keyboard",
    "PRIMARY_COINS",
    "EXTENDED_COINS",
    "chat_prompt_keyboard",
    "chat_reply_keyboard",
    "chat_clear_confirm_keyboard",
    "news_dashboard_keyboard",
    "news_coin_keyboard",
]

from .alert_keyboard import (
    alert_list_keyboard,
    alert_set_confirm_keyboard,
    alert_nav_keyboard,
    alert_delall_confirm_keyboard,
    alert_empty_keyboard,
)

__all__ += [
    "alert_list_keyboard",
    "alert_set_confirm_keyboard",
    "alert_nav_keyboard",
    "alert_delall_confirm_keyboard",
    "alert_empty_keyboard",
]
