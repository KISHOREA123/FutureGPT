"""
utils/middleware.py — Aiogram middlewares for production hardening.

Included:
  • ThrottlingMiddleware  — per-user rate limiting (in-memory)
  • LoggingMiddleware     — logs every incoming update
"""

import logging
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Simple in-memory rate limiter.

    Args:
        rate_limit: minimum seconds between messages per user.
    """

    def __init__(self, rate_limit: float = 1.0) -> None:
        self.rate_limit = rate_limit
        self._last_seen: Dict[int, float] = defaultdict(float)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
            now = time.monotonic()
            elapsed = now - self._last_seen[uid]

            if elapsed < self.rate_limit:
                logger.debug("Throttled user %s (%.2fs since last msg)", uid, elapsed)
                await event.answer(
                    f"⏳ Slow down! Please wait {self.rate_limit:.0f}s between messages."
                )
                return  # Drop the update

            self._last_seen[uid] = now

        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """Logs the type and origin of every incoming update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        uid  = user.id if user else "unknown"
        name = user.full_name if user else "?"
        logger.debug("Update from uid=%s name=%r type=%s", uid, name, type(event).__name__)
        return await handler(event, data)
