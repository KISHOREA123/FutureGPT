"""
keyboards/chat_keyboard.py — Keyboards for the AI chat feature.

Screens:
  • chat_prompt_keyboard()  — shown on the "ask a question" prompt screen
  • chat_reply_keyboard()   — shown after every AI answer (main chat UI)
  • chat_clear_keyboard()   — confirmation dialog before clearing history
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Quick-question shortcuts shown on the prompt screen
QUICK_QUESTIONS: list[tuple[str, str]] = [
    ("Should I buy BTC now?",        "ai:q:Should I buy BTC now?"),
    ("Is ETH bullish right now?",    "ai:q:Is ETH bullish right now?"),
    ("Best coins to hold long-term?","ai:q:Best coins to hold long-term?"),
    ("Explain DeFi simply",          "ai:q:Explain DeFi simply"),
]


def chat_prompt_keyboard(has_history: bool = False) -> InlineKeyboardMarkup:
    """
    Shown when the user enters the Ask AI screen.

    Layout:
      [Should I buy BTC?]  [Is ETH bullish?]
      [Best long-term?]    [Explain DeFi]
      [🗑 Clear History]   (only if has_history)
      [📊 Price]  [📈 Signal]  [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    # Quick-question 2×2 grid
    for label, cdata in QUICK_QUESTIONS:
        b.button(text=label, callback_data=cdata)
    b.adjust(2)

    # Clear history (only shown when there's something to clear)
    if has_history:
        b.row(
            InlineKeyboardButton(
                text="🗑 Clear History",
                callback_data="ai:clear",
            )
        )

    # Navigation
    b.row(
        InlineKeyboardButton(text="📊 Price",  callback_data="action:price"),
        InlineKeyboardButton(text="📈 Signal", callback_data="action:signal"),
        InlineKeyboardButton(text="🏠 Menu",   callback_data="action:menu"),
    )
    return b.as_markup()


def chat_reply_keyboard(has_history: bool = True) -> InlineKeyboardMarkup:
    """
    Shown under every AI answer.

    Layout:
      [💬 Ask Another]
      [📊 BTC Price]  [📈 BTC Signal]
      [🗑 Clear History]   (only if has_history)
      [📊 Price]  [📈 Signal]  [🏠 Menu]
    """
    b = InlineKeyboardBuilder()

    # Primary action
    b.row(InlineKeyboardButton(text="💬 Ask Another Question", callback_data="action:askai"))

    # Coin shortcuts
    b.row(
        InlineKeyboardButton(text="📊 BTC Price",   callback_data="price:BTC"),
        InlineKeyboardButton(text="📈 BTC Signal",  callback_data="signal:BTC"),
    )

    # Clear history
    if has_history:
        b.row(InlineKeyboardButton(text="🗑 Clear History", callback_data="ai:clear"))

    # Navigation
    b.row(
        InlineKeyboardButton(text="📊 Price",  callback_data="action:price"),
        InlineKeyboardButton(text="📈 Signal", callback_data="action:signal"),
        InlineKeyboardButton(text="🏠 Menu",   callback_data="action:menu"),
    )
    return b.as_markup()


def chat_clear_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Confirmation dialog before wiping history.

    Layout:
      [✅ Yes, clear it]  [❌ Cancel]
    """
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Yes, clear it", callback_data="ai:clear:confirm"),
        InlineKeyboardButton(text="❌ Cancel",         callback_data="action:askai"),
    )
    return b.as_markup()
