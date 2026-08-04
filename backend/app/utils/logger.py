"""Lightweight logging setup using loguru.

Importing `app.utils.logger` configures sensible defaults for the whole
backend. Configure via ENVIRONMENT (dev=DEBUG, prod=INFO).
"""
from __future__ import annotations

import sys

from loguru import logger

from app.core.config import settings

logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG" if settings.is_dev else "INFO",
    colorize=True,
    backtrace=settings.is_dev,
    diagnose=settings.is_dev,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
)

__all__ = ["logger"]
