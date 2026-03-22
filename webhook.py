"""
webhook.py — Production entry point using webhooks instead of polling.

Webhooks are preferred for high-traffic bots:
  • No constant polling loop
  • Telegram pushes updates instantly
  • Works behind a reverse proxy (nginx, Caddy, Traefik)

Usage:
    WEBHOOK_HOST=https://yourdomain.com \
    WEBHOOK_PATH=/webhook \
    WEB_SERVER_PORT=8080 \
    python webhook.py

Requirements (add to requirements.txt):
    aiohttp>=3.9
"""

import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import settings
from handlers import commands, callbacks
from utils.logger import setup_logger
from utils.middleware import ThrottlingMiddleware, LoggingMiddleware

# ── Webhook config from environment ───────────────────────────────────────────
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://yourdomain.com")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL  = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEB_HOST     = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_PORT     = int(os.getenv("WEB_SERVER_PORT", "8080"))


async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(WEBHOOK_URL)
    logging.getLogger(__name__).info("Webhook set → %s", WEBHOOK_URL)


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()
    logging.getLogger(__name__).info("Webhook removed")


def build_app() -> web.Application:
    setup_logger(settings.LOG_LEVEL)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))
    dp.message.middleware(LoggingMiddleware())

    dp.include_router(commands.router)
    dp.include_router(callbacks.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    return app


if __name__ == "__main__":
    web.run_app(build_app(), host=WEB_HOST, port=WEB_PORT)
