"""Logging helpers for the ELT pipeline."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


_LOG_DIR = Path("logs")
_LOG_FILE = _LOG_DIR / "elt_pipeline.log"


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Create or retrieve a configured logger.

    The logger writes to both the console and a rotating log file in the
    repository's ``logs/`` directory. This avoids import-time crashes when the
    package is imported without the directory existing yet.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level or logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    _LOG_DIR.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
