"""
handlers/digest_handler.py — Daily digest subscription management.

Commands:
  /digest          → show subscription status + toggle
  /digest on       → subscribe (digest at 8 AM UTC)
  /digest on 14    → subscribe at 2 PM UTC
  /digest off      → unsubscribe
  /digest now      → send digest immediately (preview)

Callbacks:
  digest:on:<hour>  → subscribe at hour
  digest:off        → unsubscribe
  digest:now        → send immediately
  digest:settings   → show time picker
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.digest_store import get_profile, set_digest
from services.digest_service import build_daily_digest

logger = logging.getLogger(__name__)
router = Router(name="digest")


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _digest_status_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if enabled:
        b.row(InlineKeyboardButton(text="🔕 Unsubscribe",      callback_data="digest:off"))
        b.row(InlineKeyboardButton(text="⏰ Change Time",       callback_data="digest:settings"))
    else:
        b.row(InlineKeyboardButton(text="✅ Subscribe (8 AM UTC)", callback_data="digest:on:8"))
        b.row(InlineKeyboardButton(text="⏰ Choose Time",        callback_data="digest:settings"))
    b.row(
        InlineKeyboardButton(text="📋 Preview Now",  callback_data="digest:now"),
        InlineKeyboardButton(text="🏠 Menu",         callback_data="action:menu"),
    )
    return b.as_markup()


def _time_picker_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    hours = [0, 4, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20]
    for h in hours:
        b.button(text=f"{h:02d}:00 UTC", callback_data=f"digest:on:{h}")
    b.adjust(3)
    b.row(InlineKeyboardButton(text="❌ Cancel", callback_data="digest:status"))
    return b.as_markup()


# ── Status text ───────────────────────────────────────────────────────────────

def _status_text(uid: int) -> str:
    p = get_profile(uid)
    if p.digest_enabled:
        return (
            "📰 <b>Daily Digest</b>  ✅ <i>Subscribed</i>\n\n"
            f"⏰ Delivery: <b>{p.digest_hour:02d}:00 UTC</b> every day\n\n"
            "Your morning briefing includes:\n"
            "  📊 BTC · ETH · SOL prices\n"
            "  🚀 Top 3 gainers + losers\n"
            "  🧠 BTC market sentiment\n"
            "  🔔 Your active alerts\n\n"
            "<i>Tap Preview to see it now.</i>"
        )
    return (
        "📰 <b>Daily Digest</b>  ❌ <i>Not subscribed</i>\n\n"
        "Get a morning briefing every day including:\n"
        "  📊 BTC · ETH · SOL prices\n"
        "  🚀 Top 3 gainers + top 3 losers\n"
        "  🧠 BTC market sentiment score\n"
        "  🔔 Reminder of your active alerts\n\n"
        "<i>Choose a delivery time to subscribe.</i>"
    )


# ── Command ───────────────────────────────────────────────────────────────────

@router.message(Command("digest"))
async def cmd_digest(message: Message) -> None:
    uid   = message.from_user.id
    parts = (message.text or "").split()

    if len(parts) >= 2:
        sub_cmd = parts[1].lower()

        if sub_cmd == "off":
            set_digest(uid, False)
            await message.answer("🔕 <b>Daily digest unsubscribed.</b>", reply_markup=_digest_status_keyboard(False))
            return

        if sub_cmd in ("on", "subscribe"):
            hour = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 8
            hour = max(0, min(23, hour))
            set_digest(uid, True, hour)
            await message.answer(
                f"✅ <b>Daily digest subscribed!</b>\n\nYou'll receive your briefing at <b>{hour:02d}:00 UTC</b> every day.",
                reply_markup=_digest_status_keyboard(True),
            )
            return

        if sub_cmd == "now":
            loading = await message.answer("⏳ Building your digest…")
            text    = await build_daily_digest(uid)
            await loading.edit_text(text, reply_markup=_digest_status_keyboard(get_profile(uid).digest_enabled))
            return

    p = get_profile(uid)
    await message.answer(_status_text(uid), reply_markup=_digest_status_keyboard(p.digest_enabled))


# ── Callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "digest:status")
async def cb_digest_status(query: CallbackQuery) -> None:
    await query.answer()
    uid = query.from_user.id
    p   = get_profile(uid)
    try:
        await query.message.edit_text(_status_text(uid), reply_markup=_digest_status_keyboard(p.digest_enabled))
    except Exception:
        pass


@router.callback_query(F.data == "digest:off")
async def cb_digest_off(query: CallbackQuery) -> None:
    uid = query.from_user.id
    set_digest(uid, False)
    await query.answer("🔕 Unsubscribed")
    try:
        await query.message.edit_text(_status_text(uid), reply_markup=_digest_status_keyboard(False))
    except Exception:
        pass


@router.callback_query(F.data.startswith("digest:on:"))
async def cb_digest_on(query: CallbackQuery) -> None:
    uid  = query.from_user.id
    hour = int(query.data.split(":")[-1])
    set_digest(uid, True, hour)
    await query.answer(f"✅ Subscribed at {hour:02d}:00 UTC")
    try:
        await query.message.edit_text(_status_text(uid), reply_markup=_digest_status_keyboard(True))
    except Exception:
        pass


@router.callback_query(F.data == "digest:settings")
async def cb_digest_settings(query: CallbackQuery) -> None:
    await query.answer()
    try:
        await query.message.edit_text(
            "⏰ <b>Choose your digest delivery time (UTC):</b>",
            reply_markup=_time_picker_keyboard(),
        )
    except Exception:
        pass


@router.callback_query(F.data == "digest:now")
async def cb_digest_now(query: CallbackQuery) -> None:
    uid = query.from_user.id
    await query.answer("⏳ Building digest…")
    try:
        await query.message.edit_text("⏳ <b>Building your digest…</b>\n<code>▓▓▓▓▓░░░░░  50%</code>")
    except Exception:
        pass
    text = await build_daily_digest(uid)
    p    = get_profile(uid)
    try:
        await query.message.edit_text(text, reply_markup=_digest_status_keyboard(p.digest_enabled))
    except Exception:
        await query.message.answer(text, reply_markup=_digest_status_keyboard(p.digest_enabled))
