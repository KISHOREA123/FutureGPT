"""
handlers/commands.py — Slash-command handlers.
"""

import logging
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

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
    get_general_news, get_coin_news, coin_news_not_found,
    VALID_SYMBOLS,
)
from utils.ui import cmd_placeholder, render, render_error

logger = logging.getLogger(__name__)
router = Router(name="commands")

WELCOME_TEXT = (
    "🚀 <b>FutureGPT Bot</b>  ·  Your AI Crypto Assistant\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "📊 <b>Price</b>    — Live prices via Binance\n"
    "📈 <b>Signal</b>   — AI signals (RSI · MACD · EMA)\n"
    "📰 <b>News</b>     — Hot crypto headlines\n"
    "💬 <b>Ask AI</b>   — Chat with FutureGPT\n"
    "🔍 <b>Analyze</b>  — Full coin analysis + sentiment\n"
    "🔔 <b>Alerts</b>   — Price alert notifications\n"
    "📰 <b>Digest</b>   — Daily morning briefing\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "<i>Tap a button or a coin to get started ↓</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    uid = message.from_user.id
    logger.info("User %s → /start", uid)
    # Show onboarding for first-time users
    from handlers.onboarding_handler import should_show_onboarding, send_onboarding
    if should_show_onboarding(uid):
        await send_onboarding(message)
    else:
        await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🤖 <b>FutureGPT Bot — Commands</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Prices  (Binance live)</b>\n"
        "/price                 — Dashboard (top coins)\n"
        "/price <code>BTC</code>              — Single coin card\n\n"
        "<b>Signals  (RSI · MACD · EMA)</b>\n"
        "/signal                — Overview\n"
        "/signal <code>ETH</code>             — Full breakdown\n\n"
        "<b>News</b>\n"
        "/news                  — Hot headlines\n"
        "/news <code>SOL</code>               — Coin-specific news\n\n"
        "<b>🔔 Price Alerts</b>\n"
        "/setalert <code>BTC 70000</code>     — Alert when BTC hits $70k\n"
        "/setalert <code>ETH 3500</code>      — Alert when ETH hits $3,500\n"
        "/listalerts            — View your active alerts\n"
        "/deletealert <code>&lt;id&gt;</code>      — Delete alert by ID\n"
        "/clearalerts           — Delete all alerts\n\n"
        "<b>🔍 Analyze</b>\n"
        "/analyze               — Search & analyze any coin\n"
        "/analyze <code>BTC</code>             — Direct coin analysis\n\n"
        "<b>📰 Daily Digest</b>\n"
        "/digest                — Subscribe to morning briefing\n"
        "/digest now            — Preview your digest\n\n"
        "<b>🎓 Tutorial</b>\n"
        "/tour                  — Replay onboarding tutorial\n\n"
        "<b>Other</b>\n"
        "/start                 — Home menu\n"
        "/help                  — This screen\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>⚠️ Alerts are informational only — not financial advice.</i>",
        reply_markup=main_menu_keyboard(),
    )


# ── /price ────────────────────────────────────────────────────────────────────

@router.message(Command("price"))
async def cmd_price(message: Message) -> None:
    parts  = (message.text or "").split(maxsplit=1)
    symbol = parts[1].upper().replace("USDT", "").strip() if len(parts) > 1 else ""
    placeholder = await cmd_placeholder(message, "price")

    if not symbol:
        logger.info("User %s → /price dashboard", message.from_user.id)
        try:
            text = await get_price_dashboard()
            await render(placeholder, text, price_dashboard_keyboard())
        except Exception as exc:
            logger.error("Price dashboard error: %s", exc)
            await render_error(placeholder, "Price Fetch Failed",
                               "Could not reach Binance.", retry_data="action:price")
        return

    logger.info("User %s → /price %s", message.from_user.id, symbol)
    try:
        text = await get_single_price(symbol)
        await render(placeholder, text, price_detail_keyboard(symbol))
    except InvalidSymbolError:
        await render(placeholder, invalid_symbol_message(symbol), price_dashboard_keyboard())
    except Exception as exc:
        logger.error("Price error for %s: %s", symbol, exc)
        await render_error(placeholder, "Binance API Error",
                           f"Could not fetch {symbol}/USDT.", retry_data=f"price:{symbol}")


# ── /signal ───────────────────────────────────────────────────────────────────

@router.message(Command("signal"))
async def cmd_signal(message: Message) -> None:
    parts  = (message.text or "").split(maxsplit=1)
    symbol = parts[1].upper().replace("USDT", "").strip() if len(parts) > 1 else ""
    mode   = "signal_overview" if not symbol else "signal"
    placeholder = await cmd_placeholder(message, mode)

    if not symbol:
        logger.info("User %s → /signal overview", message.from_user.id)
        try:
            text = await get_signal_overview()
            await render(placeholder, text, signal_dashboard_keyboard())
        except Exception as exc:
            logger.error("Signal overview error: %s", exc)
            await render_error(placeholder, "Signal Analysis Failed",
                               "Could not compute signals.", retry_data="action:signal")
        return

    logger.info("User %s → /signal %s", message.from_user.id, symbol)
    try:
        text = await get_single_signal(symbol)
        await render(placeholder, text, signal_detail_keyboard(symbol))
    except InvalidSymbolError:
        await render(placeholder, invalid_signal_message(symbol), signal_dashboard_keyboard())
    except Exception as exc:
        logger.error("Signal error for %s: %s", symbol, exc)
        await render_error(placeholder, "Signal Computation Failed",
                           f"Could not analyse {symbol}.", retry_data=f"signal:{symbol}")


# ── /news ─────────────────────────────────────────────────────────────────────

@router.message(Command("news"))
async def cmd_news(message: Message) -> None:
    parts  = (message.text or "").split(maxsplit=1)
    symbol = parts[1].upper().replace("USDT", "").strip() if len(parts) > 1 else ""

    if not symbol:
        logger.info("User %s → /news dashboard", message.from_user.id)
        placeholder = await cmd_placeholder(message, "news")
        try:
            text = await get_general_news()
            await render(placeholder, text, news_dashboard_keyboard())
        except Exception as exc:
            logger.error("News dashboard error: %s", exc)
            await render_error(placeholder, "News Unavailable",
                               "Could not load headlines.", retry_data="action:news")
        return

    if symbol not in VALID_SYMBOLS:
        await message.answer(coin_news_not_found(symbol), reply_markup=news_dashboard_keyboard())
        return

    logger.info("User %s → /news %s", message.from_user.id, symbol)
    placeholder = await cmd_placeholder(message, "news_coin")
    try:
        text = await get_coin_news(symbol)
        await render(placeholder, text, news_coin_keyboard(symbol))
    except Exception as exc:
        logger.error("Coin news error for %s: %s", symbol, exc)
        await render_error(placeholder, "News Unavailable",
                           f"Could not fetch {symbol} headlines.", retry_data=f"news:{symbol}")