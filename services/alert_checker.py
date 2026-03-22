"""
services/alert_checker.py — Background price-check loop for user alerts.

Architecture:
  • Runs as a single asyncio.Task started at bot startup.
  • Every CHECK_INTERVAL seconds it:
      1. Collects all active alerts from alert_store
      2. Fetches the current price for each unique symbol (one Binance call each)
      3. Compares price against each alert's target + direction
      4. For triggered alerts: sends the user a notification via bot.send_message()
      5. Removes triggered alerts from the store
  • Batches symbol fetches: if 3 users have BTC alerts only 1 Binance call is made.
  • Gracefully handles API failures: a failed fetch skips that symbol's alerts,
    they remain active and will be checked again next cycle.
  • Cancellation-safe: CancelledError propagates cleanly on bot shutdown.

No auto-trading, no side effects beyond sending Telegram messages.
"""

import asyncio
import logging
from collections import defaultdict

import aiohttp

from services.alert_store import (
    Alert,
    Direction,
    get_all_alerts,
    remove_triggered,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 60      # seconds between price checks
BINANCE_PRICE  = "https://api.binance.com/api/v3/ticker/price"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=8)


# ── Price fetcher ─────────────────────────────────────────────────────────────

async def _fetch_price(symbol: str) -> float | None:
    """
    Fetch the latest price for `symbol`/USDT from Binance.
    Returns None on any error (alert stays active, checked next cycle).
    """
    pair = f"{symbol}USDT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                BINANCE_PRICE,
                params={"symbol": pair},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    logger.debug("Binance price fetch HTTP %s for %s", resp.status, pair)
                    return None
                data = await resp.json()
                return float(data["price"])
    except Exception as exc:
        logger.debug("Price fetch error for %s: %s", pair, exc)
        return None


# ── Trigger check ─────────────────────────────────────────────────────────────

def _is_triggered(alert: Alert, price: float) -> bool:
    """Return True if `price` satisfies the alert's trigger condition."""
    if alert.direction == Direction.ABOVE:
        return price >= alert.target
    return price <= alert.target


# ── Main loop ─────────────────────────────────────────────────────────────────

async def run_alert_checker(bot) -> None:
    """
    Infinite async loop — runs for the lifetime of the bot.

    Args:
        bot: aiogram Bot instance (used to send Telegram messages).

    Call via:
        asyncio.create_task(run_alert_checker(bot))
    """
    logger.info("Alert checker started (interval=%ds)", CHECK_INTERVAL)

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)
            await _check_cycle(bot)
        except asyncio.CancelledError:
            logger.info("Alert checker cancelled — shutting down")
            raise
        except Exception as exc:
            # Never let the loop die — log and keep running
            logger.error("Alert checker unexpected error: %s", exc, exc_info=True)


async def _check_cycle(bot) -> None:
    """
    One full check cycle:
      1. Collect all active alerts
      2. Fetch prices for unique symbols
      3. Evaluate each alert
      4. Fire + remove triggered alerts
    """
    all_alerts = get_all_alerts()
    if not all_alerts:
        return   # nothing to check

    logger.debug("Alert check cycle — %d active alerts", len(all_alerts))

    # ── Group alerts by symbol to minimise API calls ──────────────────────────
    by_symbol: dict[str, list[Alert]] = defaultdict(list)
    for alert in all_alerts:
        by_symbol[alert.symbol].append(alert)

    # ── Fetch current price per unique symbol ─────────────────────────────────
    prices: dict[str, float] = {}
    for symbol in by_symbol:
        price = await _fetch_price(symbol)
        if price is not None:
            prices[symbol] = price
        await asyncio.sleep(0.1)   # tiny gap to avoid hammering Binance

    # ── Evaluate alerts and collect those that fired ──────────────────────────
    triggered: list[Alert] = []
    for symbol, alerts in by_symbol.items():
        price = prices.get(symbol)
        if price is None:
            continue   # API failed for this symbol — try again next cycle

        for alert in alerts:
            if _is_triggered(alert, price):
                triggered.append(alert)
                logger.info(
                    "Alert #%d fired: uid=%s %s %s $%.2f (actual $%.2f)",
                    alert.alert_id, alert.uid, alert.symbol,
                    alert.direction.value, alert.target, price,
                )

    if not triggered:
        return

    # ── Remove triggered alerts from store ───────────────────────────────────
    # Do this BEFORE sending messages so a restart can't double-fire
    remove_triggered(triggered)

    # ── Send notification to each user ───────────────────────────────────────
    for alert in triggered:
        price = prices[alert.symbol]
        try:
            await bot.send_message(
                chat_id=alert.uid,
                text=alert.triggered_message(price),
            )
            logger.info("Notification sent: uid=%s alert_id=%s", alert.uid, alert.alert_id)
        except Exception as exc:
            logger.warning(
                "Failed to send alert notification uid=%s: %s", alert.uid, exc
            )
