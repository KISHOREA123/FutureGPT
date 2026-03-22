"""
handlers/onboarding_handler.py — Step-by-step onboarding tutorial for new users.

Flow:
  /start (first time) → onboarding step 1
  onboard:1 → onboard:2 → ... → onboard:5 → main menu

  Or: /tour at any time to replay the tutorial.

Steps:
  1. Welcome — what FutureGPT does
  2. Prices  — show /price demo
  3. Signals — show /signal demo
  4. Alerts  — show /setalert demo
  5. AI Chat — show Ask AI demo
  Done → main menu
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from services.digest_store import is_onboarding_done, mark_onboarding_done
from keyboards.kb import main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="onboarding")

# ── Step definitions ──────────────────────────────────────────────────────────

STEPS = [
    {
        "title":   "👋 Welcome to FutureGPT Bot!",
        "content": (
            "I'm your AI-powered crypto assistant. Here's what I can do:\n\n"
            "  📊 <b>Live prices</b> from Binance\n"
            "  📈 <b>AI signals</b> with RSI · MACD · EMA\n"
            "  📰 <b>Crypto news</b> filtered by coin\n"
            "  🔔 <b>Price alerts</b> — notified instantly\n"
            "  💬 <b>AI chat</b> — ask anything about crypto\n"
            "  🔍 <b>Analyze any coin</b> with sentiment score\n\n"
            "Let me show you each feature quickly."
        ),
        "step_num": 1,
    },
    {
        "title":   "📊 Step 1 — Live Prices",
        "content": (
            "Get live prices for any coin straight from Binance.\n\n"
            "<b>Try it:</b>\n"
            "  <code>/price BTC</code>  — Bitcoin price card\n"
            "  <code>/price ETH</code>  — Ethereum price card\n"
            "  <code>/price</code>      — Top coins dashboard\n\n"
            "Or tap <b>📊 Price</b> on the main menu and pick any coin.\n\n"
            "You'll see: current price, 24h change, high/low, and volume."
        ),
        "step_num": 2,
    },
    {
        "title":   "📈 Step 2 — AI Trading Signals",
        "content": (
            "Get BUY / SELL / HOLD signals powered by technical analysis.\n\n"
            "<b>Try it:</b>\n"
            "  <code>/signal BTC</code>  — Full signal breakdown\n"
            "  <code>/signal</code>      — Overview for top 5 coins\n\n"
            "Each signal shows:\n"
            "  📐 RSI (overbought/oversold)\n"
            "  📉 MACD crossover direction\n"
            "  📈 EMA trend (20 vs 50 period)\n"
            "  🧠 Confidence score 0–80%\n\n"
            "<i>⚠️ Signals are informational only. Always DYOR.</i>"
        ),
        "step_num": 3,
    },
    {
        "title":   "🔔 Step 3 — Price Alerts",
        "content": (
            "Set alerts and get notified the moment a price is hit.\n\n"
            "<b>Try it:</b>\n"
            "  <code>/setalert BTC 70000</code>\n"
            "  <code>/setalert ETH 3500</code>\n\n"
            "The bot checks prices every 60 seconds.\n"
            "When triggered, you'll receive:\n\n"
            "<code>🚨 BTC Alert Triggered!\n"
            "🎯 Target: $70,000\n"
            "💰 Price reached: $70,043</code>\n\n"
            "Manage alerts: /listalerts · /deletealert · /clearalerts"
        ),
        "step_num": 4,
    },
    {
        "title":   "💬 Step 4 — AI Chat + Analyze",
        "content": (
            "<b>Ask AI anything about crypto:</b>\n"
            "  💬 Tap <b>Ask AI</b> on the main menu\n"
            "  Type: <i>\"Should I buy BTC now?\"</i>\n"
            "  Or: <i>\"Explain DeFi in simple terms\"</i>\n\n"
            "<b>Full coin analysis:</b>\n"
            "  🔍 Tap <b>Analyze</b> → pick any coin\n"
            "  See: Price + Signal + Sentiment + Chart Patterns\n\n"
            "<b>Daily Digest:</b>\n"
            "  Use /digest to subscribe to a morning briefing\n"
            "  Get top movers + sentiment + your alerts every day\n\n"
            "You're all set! Tap <b>Get Started</b> to go to the main menu."
        ),
        "step_num": 5,
    },
]

TOTAL_STEPS = len(STEPS)


# ── Keyboards ─────────────────────────────────────────────────────────────────

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _step_keyboard(step_num: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    nav = []

    if step_num > 1:
        nav.append(InlineKeyboardButton(
            text="⬅️ Back",
            callback_data=f"onboard:{step_num - 1}",
        ))

    if step_num < TOTAL_STEPS:
        nav.append(InlineKeyboardButton(
            text=f"Next ({step_num}/{TOTAL_STEPS}) ➡️",
            callback_data=f"onboard:{step_num + 1}",
        ))
    else:
        nav.append(InlineKeyboardButton(
            text="🚀 Get Started!",
            callback_data="onboard:done",
        ))

    b.row(*nav)

    if step_num > 1:
        b.row(InlineKeyboardButton(
            text="⏭ Skip Tour",
            callback_data="onboard:done",
        ))

    return b.as_markup()


def _build_step_text(step: dict) -> str:
    num   = step["step_num"]
    total = TOTAL_STEPS
    dots  = "●" * num + "○" * (total - num)
    return (
        f"<b>{step['title']}</b>\n"
        f"<i>{dots}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{step['content']}"
    )


# ── Public helpers ────────────────────────────────────────────────────────────

def should_show_onboarding(uid: int) -> bool:
    return not is_onboarding_done(uid)


async def send_onboarding(message: Message) -> None:
    """Send step 1 of onboarding as a new message."""
    step = STEPS[0]
    await message.answer(
        _build_step_text(step),
        reply_markup=_step_keyboard(1),
    )


# ── Handlers ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("onboard:"))
async def cb_onboard_step(query: CallbackQuery) -> None:
    step_key = query.data.split(":", 1)[1]
    await query.answer()

    if step_key == "done":
        mark_onboarding_done(query.from_user.id)
        logger.info("User %s completed onboarding", query.from_user.id)
        try:
            await query.message.edit_text(
                "🎉 <b>You're all set!</b>\n\n"
                "Use the menu below to explore FutureGPT Bot.",
                reply_markup=main_menu_keyboard(),
            )
        except Exception:
            await query.message.answer(
                "🎉 <b>You're all set!</b>",
                reply_markup=main_menu_keyboard(),
            )
        return

    try:
        step_num = int(step_key)
    except ValueError:
        return

    if not (1 <= step_num <= TOTAL_STEPS):
        return

    step = STEPS[step_num - 1]
    try:
        await query.message.edit_text(
            _build_step_text(step),
            reply_markup=_step_keyboard(step_num),
        )
    except Exception:
        pass


@router.message(Command("tour"))
async def cmd_tour(message: Message) -> None:
    """Replay the onboarding tutorial at any time."""
    step = STEPS[0]
    await message.answer(
        _build_step_text(step),
        reply_markup=_step_keyboard(1),
    )
