"""
utils/ui.py — Centralised UI rendering engine.

Responsibilities:
  • show_loading()     — edit message to a spinner screen immediately
  • render()           — edit message to final content + keyboard
  • render_error()     — edit message to a formatted error card
  • cmd_render()       — for command handlers: send a placeholder then edit it
                         (gives the same edit-in-place UX from text commands)

All functions accept either a CallbackQuery or a Message and do the right
thing — so handlers never have to branch on message type.

Loading animations use Unicode block spinners so the UI feels alive even
while waiting for Binance API calls.
"""

import logging
from typing import Union

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.exceptions import TelegramBadRequest

from keyboards.kb import error_keyboard

logger = logging.getLogger(__name__)

# ── Loading screens ────────────────────────────────────────────────────────────

_LOADING_SCREENS: dict[str, str] = {
    "price": (
        "⏳ <b>Fetching live price…</b>\n\n"
        "<i>Connecting to Binance · Please wait</i>\n\n"
        "<code>▓▓▓▓░░░░░░  40%</code>"
    ),
    "signal": (
        "⏳ <b>Analysing market…</b>\n\n"
        "<i>Fetching Binance klines\n"
        "Computing RSI · MACD · EMA · Please wait</i>\n\n"
        "<code>▓▓▓▓▓▓░░░░  60%</code>"
    ),
    "signal_overview": (
        "⏳ <b>Scanning all markets…</b>\n\n"
        "<i>Running indicators across top coins\n"
        "This may take a few seconds</i>\n\n"
        "<code>▓▓▓▓░░░░░░  40%</code>"
    ),
    "news": (
        "⏳ <b>Loading latest news…</b>\n\n"
        "<i>Fetching crypto headlines · Please wait</i>\n\n"
        "<code>▓▓▓▓▓░░░░░  50%</code>"
    ),
    "news_coin": (
        "⏳ <b>Fetching coin news…</b>\n\n"
        "<i>Scanning headlines · Filtering by coin · Please wait</i>\n\n"
        "<code>▓▓▓▓▓▓░░░░  60%</code>"
    ),
    "ai": (
        "🤔 <b>CoinGPT AI is thinking…</b>\n\n"
        "<i>Processing your question</i>\n\n"
        "<code>▓▓▓▓▓▓▓░░░  70%</code>"
    ),
    "generic": (
        "⏳ <b>Loading…</b>\n\n"
        "<code>▓▓▓▓░░░░░░  40%</code>"
    ),
}

# ── Core helpers ──────────────────────────────────────────────────────────────

async def _safe_edit(message: Message, text: str, **kwargs) -> None:
    """
    Edit a message, silently ignoring 'message not modified' errors.
    Telegram raises if you try to edit a message to its exact current content.
    """
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            logger.debug("Skipped no-op edit on message %s", message.message_id)
        else:
            logger.warning("edit_text failed: %s", exc)
            # Fall back to a new message in the same chat
            await message.answer(text, **kwargs)
    except Exception as exc:
        logger.warning("Unexpected edit error: %s", exc)
        try:
            await message.answer(text, **kwargs)
        except Exception:
            pass


def _get_message(source: Union[CallbackQuery, Message]) -> Message:
    """Extract the underlying Message from either a callback or a message."""
    if isinstance(source, CallbackQuery):
        return source.message
    return source


# ── Public API ────────────────────────────────────────────────────────────────

async def show_loading(
    source: Union[CallbackQuery, Message],
    mode: str = "generic",
) -> None:
    """
    Immediately edit the current message to a loading spinner.
    Call this before any slow async operation.

    Args:
        source: CallbackQuery or Message (from a command placeholder)
        mode:   key into _LOADING_SCREENS — "price", "signal", "news", "ai"
    """
    text = _LOADING_SCREENS.get(mode, _LOADING_SCREENS["generic"])
    msg  = _get_message(source)
    await _safe_edit(msg, text)


async def render(
    source: Union[CallbackQuery, Message],
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    """
    Edit the current message to `text` with `keyboard` attached.
    This is the final step of every callback flow.
    """
    msg = _get_message(source)
    await _safe_edit(msg, text, reply_markup=keyboard, disable_web_page_preview=True)


async def render_error(
    source: Union[CallbackQuery, Message],
    title: str,
    detail: str,
    retry_data: str,
) -> None:
    """
    Edit the current message to a standardised error card.

    Args:
        title:      Short error title, e.g. "Binance API Error"
        detail:     One-line explanation shown in italics
        retry_data: callback_data for the 🔄 Try Again button
    """
    text = (
        f"⚠️ <b>{title}</b>\n\n"
        f"<i>{detail}</i>\n\n"
        f"Tap <b>Try Again</b> or choose another option below."
    )
    msg = _get_message(source)
    await _safe_edit(msg, text, reply_markup=error_keyboard(retry_data))


async def cmd_placeholder(message: Message, mode: str = "generic") -> Message:
    """
    For command handlers: send an initial loading message and return it.
    The returned Message can then be passed to show_loading() + render().

    Usage:
        placeholder = await cmd_placeholder(message, "price")
        data = await fetch_something()
        await render(placeholder, data, keyboard)
    """
    text = _LOADING_SCREENS.get(mode, _LOADING_SCREENS["generic"])
    return await message.answer(text)
