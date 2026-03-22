"""
handlers/callbacks.py — Price, Signal, and News callback handlers.

The AI chat callbacks (action:askai, ai:*, FSM) live in handlers/chat_handler.py
which is registered before this router.

Every handler follows the 4-step pattern:
  1. query.answer()          — dismiss Telegram's loading spinner instantly
  2. show_loading(query, …)  — edit the message to a spinner screen
  3. async service call      — fetch / compute data
  4. render(query, text, kb) — edit message to final content + keyboard
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import (
    main_menu_keyboard,
    price_dashboard_keyboard,
    price_detail_keyboard,
    signal_dashboard_keyboard,
    signal_detail_keyboard,
    news_dashboard_keyboard,
    news_coin_keyboard,
)
from services import (
    get_single_price, get_price_dashboard,
    invalid_symbol_message, InvalidSymbolError,
    get_single_signal, get_signal_overview,
    invalid_signal_message,
    get_general_news, get_coin_news,
    VALID_SYMBOLS,
)
from utils.ui import show_loading, render, render_error

logger = logging.getLogger(__name__)
router = Router(name="callbacks")

WELCOME_TEXT = (
    "🚀 <b>FutureGPT Bot</b>  ·  Your AI Crypto Assistant\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "📊 <b>Price</b>   — Live prices via Binance\n"
    "📈 <b>Signal</b>  — AI signals (RSI · MACD · EMA)\n"
    "📰 <b>News</b>    — Hot crypto headlines\n"
    "💬 <b>Ask AI</b>  — Chat with FutureGPT\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "<i>Tap a button or a coin to get started ↓</i>"
)


# ─────────────────────────────────────────────────────────────────────────────
# 🏠  MENU
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "action:menu")
async def cb_menu(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.answer()
    await render(query, WELCOME_TEXT, main_menu_keyboard())


# ─────────────────────────────────────────────────────────────────────────────
# 📊  PRICE — dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "action:price")
async def cb_price_dashboard(query: CallbackQuery) -> None:
    await query.answer("📊 Loading dashboard…")
    logger.info("User %s → price dashboard", query.from_user.id)
    await show_loading(query, "price")
    try:
        text = await get_price_dashboard()
        await render(query, text, price_dashboard_keyboard())
    except Exception as exc:
        logger.error("Price dashboard error: %s", exc)
        await render_error(
            query, "Price Fetch Failed",
            "Could not reach Binance. Please try again.",
            retry_data="action:price",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 📊  PRICE — single coin
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("price:"))
async def cb_price_coin(query: CallbackQuery) -> None:
    symbol = query.data.split(":", 1)[1].upper()
    await query.answer(f"📊 {symbol} price…")
    logger.info("User %s → price:%s", query.from_user.id, symbol)
    await show_loading(query, "price")
    try:
        text = await get_single_price(symbol)
        await render(query, text, price_detail_keyboard(symbol))
    except InvalidSymbolError:
        await render(query, invalid_symbol_message(symbol), price_dashboard_keyboard())
    except Exception as exc:
        logger.error("Price error for %s: %s", symbol, exc)
        await render_error(
            query, "Binance API Error",
            f"Could not fetch {symbol}/USDT. Try again shortly.",
            retry_data=f"price:{symbol}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 📈  SIGNAL — overview
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "action:signal")
async def cb_signal_overview(query: CallbackQuery) -> None:
    await query.answer("📈 Scanning markets…")
    logger.info("User %s → signal overview", query.from_user.id)
    await show_loading(query, "signal_overview")
    try:
        text = await get_signal_overview()
        await render(query, text, signal_dashboard_keyboard())
    except Exception as exc:
        logger.error("Signal overview error: %s", exc)
        await render_error(
            query, "Signal Analysis Failed",
            "Could not compute signals. Binance may be temporarily unavailable.",
            retry_data="action:signal",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 📈  SIGNAL — single coin
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("signal:"))
async def cb_signal_coin(query: CallbackQuery) -> None:
    symbol = query.data.split(":", 1)[1].upper()
    await query.answer(f"📈 Analysing {symbol}…")
    logger.info("User %s → signal:%s", query.from_user.id, symbol)
    await show_loading(query, "signal")
    try:
        text = await get_single_signal(symbol)
        await render(query, text, signal_detail_keyboard(symbol))
    except InvalidSymbolError:
        await render(query, invalid_signal_message(symbol), signal_dashboard_keyboard())
    except Exception as exc:
        logger.error("Signal error for %s: %s", symbol, exc)
        await render_error(
            query, "Signal Computation Failed",
            f"Could not analyse {symbol}/USDT. Try again shortly.",
            retry_data=f"signal:{symbol}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 📰  NEWS — general dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "action:news")
async def cb_news_dashboard(query: CallbackQuery) -> None:
    """Show general hot crypto news with coin-filter buttons."""
    await query.answer("📰 Fetching headlines…")
    logger.info("User %s → news dashboard", query.from_user.id)
    await show_loading(query, "news")
    try:
        text = await get_general_news()
        await render(query, text, news_dashboard_keyboard())
    except Exception as exc:
        logger.error("News dashboard error: %s", exc)
        await render_error(
            query, "News Unavailable",
            "Could not load headlines right now.",
            retry_data="action:news",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 📰  NEWS — coin-specific
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("news:"))
async def cb_news_coin(query: CallbackQuery) -> None:
    """
    Show headlines filtered for a specific coin.
    Triggered by coin buttons on the news dashboard:  news:BTC, news:ETH …
    The Refresh button on coin screens also uses the same callback_data.
    """
    symbol = query.data.split(":", 1)[1].upper()
    await query.answer(f"📰 {symbol} headlines…")
    logger.info("User %s → news:%s", query.from_user.id, symbol)

    await show_loading(query, "news_coin")

    try:
        text = await get_coin_news(symbol)
        await render(query, text, news_coin_keyboard(symbol))
    except Exception as exc:
        logger.error("Coin news error for %s: %s", symbol, exc)
        await render_error(
            query, "News Unavailable",
            f"Could not fetch {symbol} headlines right now.",
            retry_data=f"news:{symbol}",
        )
