"""
services/alert_store.py — In-memory storage for user price alerts.

Data model:
  _alerts: dict[uid, list[Alert]]

Each Alert tracks:
  • symbol      — coin ticker (e.g. "BTC")
  • target      — target price (float)
  • direction   — "above" | "below"  (auto-detected at set time vs current price)
  • created_at  — UTC datetime
  • triggered   — False until the price check fires it

Design:
  • Pure in-memory: zero deps, survives bot restarts only with export/import.
  • asyncio-safe: single event loop, no locking needed.
  • Max MAX_ALERTS_PER_USER alerts per user — prevents abuse.
  • Triggered alerts are removed immediately after notification.
  • Swap to Redis / SQLite with zero changes to callers (same interface).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

MAX_ALERTS_PER_USER = 10


class Direction(str, Enum):
    ABOVE = "above"   # fire when price >= target
    BELOW = "below"   # fire when price <= target


@dataclass
class Alert:
    uid:        int
    symbol:     str             # e.g. "BTC"
    target:     float           # target price in USD
    direction:  Direction
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    alert_id:   int = 0         # set by store on insertion

    # ── Human-readable helpers ────────────────────────────────────────────────

    @property
    def direction_label(self) -> str:
        return "≥" if self.direction == Direction.ABOVE else "≤"

    @property
    def direction_emoji(self) -> str:
        return "📈" if self.direction == Direction.ABOVE else "📉"

    def summary(self) -> str:
        """One-line summary for /listalerts output."""
        return (
            f"#{self.alert_id}  {self.direction_emoji} "
            f"<b>{self.symbol}</b> {self.direction_label} "
            f"<code>${self.target:,.2f}</code>"
        )

    def triggered_message(self, actual_price: float) -> str:
        """Full notification message sent when the alert fires."""
        direction_word = "reached" if self.direction == Direction.ABOVE else "dropped to"
        return (
            f"🚨 <b>{self.symbol} Alert Triggered!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Target:</b>  <code>${self.target:,.2f}</code>\n"
            f"💰 <b>Price {direction_word}:</b>  <code>${actual_price:,.2f}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>⚠️ For information only — not financial advice.</i>"
        )


# ── Module-level store ────────────────────────────────────────────────────────

_alerts: dict[int, list[Alert]] = {}   # uid → list[Alert]
_next_id: int = 1                      # global monotonic alert ID counter


def _new_id() -> int:
    global _next_id
    aid = _next_id
    _next_id += 1
    return aid


# ── Public API ────────────────────────────────────────────────────────────────

class AlertLimitError(Exception):
    """Raised when a user tries to set more than MAX_ALERTS_PER_USER alerts."""


class DuplicateAlertError(Exception):
    """Raised when user sets an identical symbol+target alert they already have."""


def add_alert(
    uid: int,
    symbol: str,
    target: float,
    direction: Direction,
) -> Alert:
    """
    Create and store a new alert.

    Raises:
        AlertLimitError:     User already has MAX_ALERTS_PER_USER alerts.
        DuplicateAlertError: Identical symbol+target already exists for user.
    """
    if uid not in _alerts:
        _alerts[uid] = []

    user_alerts = _alerts[uid]

    if len(user_alerts) >= MAX_ALERTS_PER_USER:
        raise AlertLimitError(
            f"Maximum {MAX_ALERTS_PER_USER} alerts per user. "
            "Delete some with /deletealert <id> first."
        )

    # Duplicate check: same symbol + same target (within $0.01 tolerance)
    for existing in user_alerts:
        if existing.symbol == symbol and abs(existing.target - target) < 0.01:
            raise DuplicateAlertError(
                f"You already have an alert for {symbol} at ${target:,.2f}."
            )

    alert = Alert(
        uid=uid,
        symbol=symbol,
        target=target,
        direction=direction,
        alert_id=_new_id(),
    )
    user_alerts.append(alert)
    return alert


def get_user_alerts(uid: int) -> list[Alert]:
    """Return all active alerts for a user (empty list if none)."""
    return list(_alerts.get(uid, []))


def delete_alert(uid: int, alert_id: int) -> Alert | None:
    """
    Remove an alert by its ID.
    Returns the deleted Alert, or None if not found.
    """
    if uid not in _alerts:
        return None
    before = _alerts[uid]
    for alert in before:
        if alert.alert_id == alert_id:
            _alerts[uid] = [a for a in before if a.alert_id != alert_id]
            return alert
    return None


def delete_all_alerts(uid: int) -> int:
    """Delete all alerts for a user. Returns count deleted."""
    count = len(_alerts.get(uid, []))
    _alerts[uid] = []
    return count


def get_all_alerts() -> list[Alert]:
    """
    Return every active alert across all users.
    Used by the background price checker to fetch all symbols it needs.
    """
    result: list[Alert] = []
    for user_alerts in _alerts.values():
        result.extend(user_alerts)
    return result


def remove_triggered(alerts_to_remove: list[Alert]) -> None:
    """
    Bulk-remove a list of alerts that have fired.
    Called by the price checker after sending notifications.
    """
    ids_to_remove = {a.alert_id for a in alerts_to_remove}
    for uid in _alerts:
        _alerts[uid] = [a for a in _alerts[uid] if a.alert_id not in ids_to_remove]


def alert_count() -> int:
    """Total number of active alerts across all users."""
    return sum(len(v) for v in _alerts.values())
