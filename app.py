"""
app.py — Production entry point: FastAPI + aiogram webhook.

This is the file Render/Railway uses. It starts a real HTTP server
on $PORT so the platform can detect the open port and route traffic.

Architecture:
  uvicorn (ASGI) → FastAPI → POST /webhook/{secret} → aiogram → handlers

Run locally with webhook (ngrok):
  WEBHOOK_HOST=https://xxxx.ngrok-free.app uvicorn app:fastapi_app --reload

Run in production (Render / Railway):
  uvicorn app:fastapi_app --host 0.0.0.0 --port $PORT --workers 1
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from config import settings
from handlers import (
    commands, callbacks, chat_handler,
    alert_handler, analyze_handler,
    onboarding_handler, digest_handler,
)
from services.alert_checker import run_alert_checker
from services.daily_scheduler import run_daily_scheduler
from utils.logger import setup_logger
from utils.middleware import ThrottlingMiddleware, LoggingMiddleware

setup_logger(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# ── Bot + Dispatcher ──────────────────────────────────────────────────────────

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher()
dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))
dp.message.middleware(LoggingMiddleware())

# Router order matters — most specific first
dp.include_router(onboarding_handler.router)
dp.include_router(digest_handler.router)
dp.include_router(alert_handler.router)
dp.include_router(analyze_handler.router)
dp.include_router(commands.router)
dp.include_router(chat_handler.router)
dp.include_router(callbacks.router)

# ── Background tasks ──────────────────────────────────────────────────────────

_alert_task:  asyncio.Task | None = None
_digest_task: asyncio.Task | None = None


async def _start_tasks() -> None:
    global _alert_task, _digest_task
    _alert_task  = asyncio.create_task(run_alert_checker(bot),   name="alert-checker")
    _digest_task = asyncio.create_task(run_daily_scheduler(bot), name="digest-scheduler")
    logger.info("Background tasks started")


async def _stop_tasks() -> None:
    for task in (_alert_task, _digest_task):
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    logger.info("Background tasks stopped")


# ── Webhook lifecycle ─────────────────────────────────────────────────────────

async def _register_webhook() -> None:
    try:
        info = await bot.get_webhook_info()
        if info.url == settings.webhook_url:
            logger.info("Webhook already set: %s", settings.webhook_url)
            return
    except Exception:
        pass

    await bot.set_webhook(
        url=settings.webhook_url,
        secret_token=settings.WEBHOOK_SECRET,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    logger.info("Webhook registered: %s", settings.webhook_url)


async def _delete_webhook() -> None:
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Webhook deleted")
    except Exception as exc:
        logger.warning("Could not delete webhook: %s", exc)


# ── FastAPI lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "FutureGPT Bot starting  mode=%s  port=%d",
        "webhook" if settings.USE_WEBHOOK else "no-webhook",
        settings.PORT,
    )

    if settings.USE_WEBHOOK:
        await _register_webhook()
    else:
        logger.warning(
            "WEBHOOK_HOST not set — FastAPI is running but Telegram will NOT "
            "send updates here. Add WEBHOOK_HOST env var in Render dashboard."
        )

    await _start_tasks()

    yield   # app is live

    await _stop_tasks()
    if settings.USE_WEBHOOK:
        await _delete_webhook()
    await bot.session.close()
    logger.info("Bot stopped cleanly")


# ── FastAPI app ───────────────────────────────────────────────────────────────

fastapi_app = FastAPI(
    title="FutureGPT Bot",
    description="AI Crypto Telegram Bot",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


# ── Routes ────────────────────────────────────────────────────────────────────

@fastapi_app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse({
        "service":  "FutureGPT Bot",
        "status":   "running",
        "mode":     "webhook" if settings.USE_WEBHOOK else "polling-only",
        "webhook":  settings.webhook_url if settings.USE_WEBHOOK else None,
    })


@fastapi_app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)


@fastapi_app.get("/ready", include_in_schema=False)
async def ready() -> JSONResponse:
    try:
        me = await bot.get_me()
        return JSONResponse({"status": "ready", "bot_id": me.id, "username": me.username})
    except Exception as exc:
        return JSONResponse(
            {"status": "not_ready", "error": str(exc)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@fastapi_app.post(settings.WEBHOOK_PATH, include_in_schema=False)
async def telegram_webhook(request: Request) -> Response:
    # Verify Telegram's secret signature
    received = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if received != settings.WEBHOOK_SECRET:
        logger.warning("Rejected webhook request with bad secret")
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        body   = await request.json()
        update = Update.model_validate(body, context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
    except Exception as exc:
        # Always return 200 — non-2xx causes Telegram to retry endlessly
        logger.error("Update processing error: %s", exc, exc_info=True)

    return Response(status_code=status.HTTP_200_OK)


# ── Direct run ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "app:fastapi_app",
        host=settings.HOST,
        port=settings.PORT,
        workers=1,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
