"""
handlers/alert_handler.py — Price alert commands and callbacks.

Commands:
  /setalert BTC 70000    — set a price alert for BTC at $70,000
  /listalerts            — show all active alerts with delete buttons
  /deletealert 3         — delete alert #3 by ID
  /clearalerts           — delete all alerts (with confirmation)

Callbacks:
  alert:list             — re-render the alerts list (after a delete)
  alert:del:<id>         — delete a single alert by ID
  alert:delall           — show confirmation before deleting all
  alert:delall:confirm   — confirmed delete all
  alert:howto            — show usage instructions

Direction is inferred at set-time vs current Binance price:
  price set ABOVE current  → alert fires when price rises to target
  price set BELOW current  → alert fires when price falls to target
"""

import logging

import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from keyboards.alert_keyboard import (
    alert_list_keyboard,
    alert_set_confirm_keyboard,
    alert_nav_keyboard,
    alert_delall_confirm_keyboard,
    alert_empty_keyboard,
)
from services.alert_store import (
    Alert,
    Direction,
    add_alert,
    get_user_alerts,
    delete_alert,
    delete_all_alerts,
    AlertLimitError,
    DuplicateAlertError,
    MAX_ALERTS_PER_USER,
)
from services.price_service import VALID_SYMBOLS, COIN_META

logger = logging.getLogger(__name__)
router = Router(name="alerts")

BINANCE_PRICE   = "https://api.binance.com/api/v3/ticker/price"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=6)

_HOWTO_TEXT = (
    "🔔 <b>Price Alerts — How to Use</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "<b>Set an alert:</b>\n"
    "<code>/setalert BTC 70000</code>\n"
    "<code>/setalert ETH 3500</code>\n"
    "<code>/setalert SOL 200</code>\n\n"
    "<b>Manage alerts:</b>\n"
    "/listalerts         — view active alerts\n"
    "/deletealert &lt;id&gt;   — delete by ID\n"
    "/clearalerts        — delete all\n\n"
    f"<i>Max {MAX_ALERTS_PER_USER} alerts per user.\n"
    "Alerts auto-delete after triggering.\n"
    "⚠️ For information only — not financial advice.</i>"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_current_price(symbol: str) -> float | None:
    """Fetch live price from Binance. Returns None on any error."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                BINANCE_PRICE,
                params={"symbol": f"{symbol}USDT"},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return float(data["price"])
    except Exception:
        return None


def _build_alerts_text(uid: int) -> tuple[str, list[Alert]]:
    """
    Build the alert list card text + return the alert list.
    Returns (text, alerts).
    """
    alerts = get_user_alerts(uid)
    if not alerts:
        return (
            "📋 <b>Your Price Alerts</b>\n\n"
            "<i>No active alerts. Set one with:</i>\n"
            "<code>/setalert BTC 70000</code>",
            [],
        )

    lines = [
        f"📋 <b>Your Price Alerts</b>  "
        f"<i>({len(alerts)}/{MAX_ALERTS_PER_USER})</i>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for alert in alerts:
        lines.append(alert.summary())

    lines += [
        "━━━━━━━━━━━━━━━━━━━━",
        "<i>Alerts fire once then auto-delete.\n"
        "Tap a delete button or use /deletealert &lt;id&gt;</i>",
    ]
    return "\n".join(lines), alerts


# ─────────────────────────────────────────────────────────────────────────────
# /setalert  BTC  70000
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("setalert"))
async def cmd_setalert(message: Message) -> None:
    """
    Parse /setalert <SYMBOL> <PRICE> and create an alert.

    Examples:
      /setalert BTC 70000
      /setalert eth 3500.50
      /setalert SOL 200
    """
    uid  = message.from_user.id
    text = (message.text or "").split(maxsplit=2)

    # ── Argument validation ───────────────────────────────────────────────────
    if len(text) < 3:
        await message.answer(
            "⚠️ <b>Usage:</b>  <code>/setalert &lt;symbol&gt; &lt;price&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "  <code>/setalert BTC 70000</code>\n"
            "  <code>/setalert ETH 3500</code>\n"
            "  <code>/setalert SOL 200</code>",
        )
        return

    raw_symbol = text[1].upper().strip()
    raw_price  = text[2].strip().replace(",", "")   # allow "$70,000" input

    # Symbol check
    if raw_symbol not in VALID_SYMBOLS:
        from services.price_service import DASHBOARD_SYMBOLS
        popular = "  ".join(f"<code>{s}</code>" for s in DASHBOARD_SYMBOLS)
        await message.answer(
            f"⚠️ <b>Unknown symbol:</b> <code>{raw_symbol}</code>\n\n"
            f"Supported coins include:\n{popular}\n\n"
            f"<i>Usage: /setalert BTC 70000</i>",
        )
        return

    # Price check
    try:
        target = float(raw_price.lstrip("$"))
        if target <= 0:
            raise ValueError("non-positive price")
    except ValueError:
        await message.answer(
            f"⚠️ <b>Invalid price:</b> <code>{raw_price}</code>\n\n"
            "<i>Price must be a positive number, e.g. <code>70000</code></i>",
        )
        return

    # ── Fetch current price to infer direction ────────────────────────────────
    loading = await message.answer(
        f"⏳ <b>Checking current {raw_symbol} price…</b>"
    )

    current_price = await _get_current_price(raw_symbol)
    direction = (
        Direction.ABOVE if (current_price is None or target >= current_price)
        else Direction.BELOW
    )

    # ── Create the alert ──────────────────────────────────────────────────────
    try:
        alert = add_alert(uid=uid, symbol=raw_symbol, target=target, direction=direction)
    except AlertLimitError as exc:
        await loading.edit_text(f"⚠️ {exc}")
        return
    except DuplicateAlertError as exc:
        await loading.edit_text(f"⚠️ {exc}")
        return

    # ── Success confirmation ──────────────────────────────────────────────────
    meta      = COIN_META.get(raw_symbol, {"icon": "🪙", "name": raw_symbol})
    dir_label = "rises to" if direction == Direction.ABOVE else "drops to"
    dir_emoji = "📈" if direction == Direction.ABOVE else "📉"

    current_line = (
        f"📊 <b>Current:</b>  <code>${current_price:,.2f}</code>\n"
        if current_price else ""
    )

    await loading.edit_text(
        f"✅ <b>Alert Set!</b>  #{alert.alert_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 <b>Coin:</b>    {meta['icon']} {meta['name']} ({raw_symbol})\n"
        f"🎯 <b>Target:</b>  <code>${target:,.2f}</code>\n"
        f"{current_line}"
        f"{dir_emoji} <b>Fires when</b> price {dir_label} <code>${target:,.2f}</code>\n"
        f"⏱ <b>Checked:</b>  every 60 seconds\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>🔔 You'll receive a notification when it triggers.\n"
        f"⚠️ For information only — not financial advice.</i>",
        reply_markup=alert_set_confirm_keyboard(raw_symbol),
    )

    logger.info(
        "Alert set: uid=%s #%d %s %s $%.2f",
        uid, alert.alert_id, raw_symbol, direction.value, target,
    )


# ─────────────────────────────────────────────────────────────────────────────
# /listalerts
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("listalerts"))
async def cmd_listalerts(message: Message) -> None:
    uid = message.from_user.id
    logger.info("User %s → /listalerts", uid)
    text, alerts = _build_alerts_text(uid)
    kb = alert_list_keyboard(alerts) if alerts else alert_empty_keyboard()
    await message.answer(text, reply_markup=kb)


# ─────────────────────────────────────────────────────────────────────────────
# /deletealert <id>
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("deletealert"))
async def cmd_deletealert(message: Message) -> None:
    uid   = message.from_user.id
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer(
            "⚠️ <b>Usage:</b>  <code>/deletealert &lt;id&gt;</code>\n\n"
            "Find your alert IDs with /listalerts",
        )
        return

    alert_id = int(parts[1].strip())
    deleted  = delete_alert(uid, alert_id)

    if not deleted:
        await message.answer(
            f"⚠️ Alert <b>#{alert_id}</b> not found.\n\n"
            "Check your active alerts with /listalerts",
        )
        return

    meta = COIN_META.get(deleted.symbol, {"icon": "🪙", "name": deleted.symbol})
    await message.answer(
        f"🗑 <b>Alert #{deleted.alert_id} deleted</b>\n\n"
        f"{meta['icon']} {meta['name']}  {deleted.direction_label}  "
        f"<code>${deleted.target:,.2f}</code>",
        reply_markup=alert_nav_keyboard(),
    )
    logger.info("Alert deleted: uid=%s #%d", uid, alert_id)


# ─────────────────────────────────────────────────────────────────────────────
# /clearalerts
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("clearalerts"))
async def cmd_clearalerts(message: Message) -> None:
    uid    = message.from_user.id
    alerts = get_user_alerts(uid)

    if not alerts:
        await message.answer(
            "ℹ️ You have no active alerts to clear.",
            reply_markup=alert_empty_keyboard(),
        )
        return

    await message.answer(
        f"🗑 <b>Delete all {len(alerts)} alerts?</b>\n\n"
        "<i>This cannot be undone.</i>",
        reply_markup=alert_delall_confirm_keyboard(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "alert:list")
async def cb_alert_list(query: CallbackQuery) -> None:
    """Re-render the alert list in-place (after a delete or from confirm screen)."""
    await query.answer()
    uid = query.from_user.id
    text, alerts = _build_alerts_text(uid)
    kb = alert_list_keyboard(alerts) if alerts else alert_empty_keyboard()
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        await query.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "alert:howto")
async def cb_alert_howto(query: CallbackQuery) -> None:
    """Show the how-to instructions screen."""
    await query.answer()
    try:
        await query.message.edit_text(_HOWTO_TEXT, reply_markup=alert_nav_keyboard())
    except Exception:
        await query.message.answer(_HOWTO_TEXT, reply_markup=alert_nav_keyboard())


@router.callback_query(F.data.startswith("alert:del:"))
async def cb_alert_delete(query: CallbackQuery) -> None:
    """Delete a single alert by ID and re-render the list."""
    uid      = query.from_user.id
    alert_id = int(query.data.split(":")[-1])
    deleted  = delete_alert(uid, alert_id)

    if deleted:
        await query.answer(f"🗑 Alert #{alert_id} deleted")
        logger.info("Alert deleted via button: uid=%s #%d", uid, alert_id)
    else:
        await query.answer("Alert not found — may already be deleted", show_alert=True)

    # Re-render the list
    text, alerts = _build_alerts_text(uid)
    kb = alert_list_keyboard(alerts) if alerts else alert_empty_keyboard()
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass


@router.callback_query(F.data == "alert:delall")
async def cb_alert_delall_request(query: CallbackQuery) -> None:
    """Show confirmation before deleting all."""
    await query.answer()
    uid    = query.from_user.id
    alerts = get_user_alerts(uid)
    if not alerts:
        await query.answer("No alerts to delete", show_alert=True)
        return
    try:
        await query.message.edit_text(
            f"🗑 <b>Delete all {len(alerts)} alerts?</b>\n\n"
            "<i>This cannot be undone.</i>",
            reply_markup=alert_delall_confirm_keyboard(),
        )
    except Exception:
        pass


@router.callback_query(F.data == "alert:delall:confirm")
async def cb_alert_delall_confirm(query: CallbackQuery) -> None:
    """Confirmed — wipe all alerts and show empty state."""
    uid   = query.from_user.id
    count = delete_all_alerts(uid)
    await query.answer(f"🗑 {count} alert{'s' if count != 1 else ''} deleted")
    logger.info("All alerts deleted: uid=%s count=%d", uid, count)
    try:
        await query.message.edit_text(
            "🗑 <b>All alerts deleted.</b>\n\n"
            "<i>Set new alerts with /setalert</i>",
            reply_markup=alert_empty_keyboard(),
        )
    except Exception:
        pass
