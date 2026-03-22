"""
utils/logger.py — Configures the root logger for the application.
"""

import logging
import sys


def setup_logger(level: str = "INFO") -> None:
    """Call once at startup to configure structured console logging."""
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=fmt,
        datefmt=date_fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Silence noisy third-party loggers
    for lib in ("aiogram", "aiohttp", "asyncio"):
        logging.getLogger(lib).setLevel(logging.WARNING)
