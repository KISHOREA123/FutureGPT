"""
services/daily_scheduler.py — Background task that sends daily digests.

Runs as an asyncio.Task alongside the alert checker.
Every minute checks if any subscriber is due for their digest.
Digest is sent once per day at the user's preferred UTC hour.
"""

import asyncio
import logging
from datetime import datetime, timezone

from services.digest_store import get_digest_subscribers, UserProfile
from services.digest_service import build_daily_digest

logger = logging.getLogger(__name__)

# Track last sent time per user to prevent double-sends
_last_sent: dict[int, int] = {}   # uid → UTC day-of-year


async def run_daily_scheduler(bot) -> None:
    """Infinite loop — check every 60s if any digest is due."""
    logger.info("Daily digest scheduler started")

    while True:
        try:
            await asyncio.sleep(60)
            await _check_digests(bot)
        except asyncio.CancelledError:
            logger.info("Daily scheduler cancelled")
            raise
        except Exception as exc:
            logger.error("Daily scheduler error: %s", exc, exc_info=True)


async def _check_digests(bot) -> None:
    now         = datetime.now(timezone.utc)
    current_hour = now.hour
    day_of_year  = now.timetuple().tm_yday

    subscribers = get_digest_subscribers()
    if not subscribers:
        return

    for profile in subscribers:
        if profile.digest_hour != current_hour:
            continue

        # Only send once per day
        if _last_sent.get(profile.uid) == day_of_year:
            continue

        try:
            text = await build_daily_digest(profile.uid)
            await bot.send_message(chat_id=profile.uid, text=text)
            _last_sent[profile.uid] = day_of_year
            logger.info("Daily digest sent to uid=%s", profile.uid)
        except Exception as exc:
            logger.warning("Digest send failed uid=%s: %s", profile.uid, exc)
