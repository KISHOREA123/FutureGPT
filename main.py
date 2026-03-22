"""
FutureGPT Bot — Main entry point (long-polling mode).
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from handlers import commands, callbacks, chat_handler, alert_handler, analyze_handler, onboarding_handler, digest_handler
from services.alert_checker import run_alert_checker
from services.daily_scheduler import run_daily_scheduler
from utils.logger import setup_logger
from utils.middleware import ThrottlingMiddleware, LoggingMiddleware


async def main() -> None:
    setup_logger(settings.LOG_LEVEL)
    logger = logging.getLogger(__name__)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))
    dp.message.middleware(LoggingMiddleware())

    dp.include_router(onboarding_handler.router)  # onboard:* callbacks + /tour
    dp.include_router(digest_handler.router)       # /digest, digest:*
    dp.include_router(alert_handler.router)        # /setalert, alert:*
    dp.include_router(analyze_handler.router)      # action:analyze, analyze:*, FSM
    dp.include_router(commands.router)             # /start /help /price /signal /news
    dp.include_router(chat_handler.router)         # action:askai, ai:*, FSM
    dp.include_router(callbacks.router)            # price:* signal:* news:* action:*

    alert_task   = asyncio.create_task(run_alert_checker(bot))
    digest_task  = asyncio.create_task(run_daily_scheduler(bot))
    logger.info("FutureGPT Bot starting…")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        alert_task.cancel()
        digest_task.cancel()
        for t in (alert_task, digest_task):
            try:
                await t
            except asyncio.CancelledError:
                pass
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())