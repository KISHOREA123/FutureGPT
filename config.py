"""
config.py — Centralised, validated settings loaded from environment variables.

Auto-detection:
  WEBHOOK_HOST set  → webhook mode (Railway / Render / VPS)
  WEBHOOK_HOST empty → polling mode (local dev via main.py)
"""

import hashlib
import os

# Load .env file if present (safe to call even if already loaded)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed — env vars must be set manually

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # ── Required ──────────────────────────────────────────────────────────────
    BOT_TOKEN:          str

    # ── Webhook ───────────────────────────────────────────────────────────────
    WEBHOOK_HOST:       str
    WEBHOOK_PATH:       str
    WEBHOOK_SECRET:     str

    # ── Server ────────────────────────────────────────────────────────────────
    HOST:               str
    PORT:               int

    # ── Feature flags ─────────────────────────────────────────────────────────
    USE_WEBHOOK:        bool

    # ── Optional APIs ─────────────────────────────────────────────────────────
    OPENAI_API_KEY:     str
    NEWS_API_KEY:       str

    # ── Misc ──────────────────────────────────────────────────────────────────
    LOG_LEVEL:          str
    COINGECKO_BASE_URL: str

    @property
    def webhook_url(self) -> str:
        return f"{self.WEBHOOK_HOST}{self.WEBHOOK_PATH}"

    @property
    def is_production(self) -> bool:
        return self.USE_WEBHOOK

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise EnvironmentError(
                "\n"
                "  BOT_TOKEN is required but not set.\n"
                "  1. Create a .env file in the same folder as main.py\n"
                "  2. Add this line:  BOT_TOKEN=your_token_here\n"
                "  3. Get your token from @BotFather on Telegram\n"
            )

        webhook_host   = os.getenv("WEBHOOK_HOST", "").rstrip("/")
        use_webhook    = bool(webhook_host)
        webhook_secret = os.getenv("WEBHOOK_SECRET") or _derive_secret(token)
        webhook_path   = os.getenv("WEBHOOK_PATH") or f"/webhook/{webhook_secret}"

        return cls(
            BOT_TOKEN          = token,
            WEBHOOK_HOST       = webhook_host,
            WEBHOOK_PATH       = webhook_path,
            WEBHOOK_SECRET     = webhook_secret,
            HOST               = os.getenv("HOST", "0.0.0.0"),
            PORT               = int(os.getenv("PORT", "8000")),
            USE_WEBHOOK        = use_webhook,
            OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", ""),
            NEWS_API_KEY       = os.getenv("NEWS_API_KEY", ""),
            LOG_LEVEL          = os.getenv("LOG_LEVEL", "INFO").upper(),
            COINGECKO_BASE_URL = os.getenv(
                "COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3"
            ),
        )


def _derive_secret(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:32]


settings: Settings = Settings.from_env()