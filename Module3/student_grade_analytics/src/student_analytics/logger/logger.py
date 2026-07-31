"""Centralised logging configuration for the analytics package.

Uses the standard library's :mod:`logging` module so that host applications
can freely override handlers, formatters, and log levels without importing
third-party packages.

Logs are written both to stderr and to a rotating log file under the
project's ``logs/`` directory.
"""

import logging
import sys
from pathlib import Path
from typing import Final

_DEFAULT_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
_DEFAULT_DATE_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%S%z"

_LOG_DIR: Final[Path] = Path(__file__).resolve().parent.parent.parent / "logs"
_LOG_FILE: Final[Path] = _LOG_DIR / "student_analytics.log"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the package logger with stream and file handlers.

    The function is safe to call multiple times — repeated calls simply
    replace the existing handlers on the root ``student_analytics`` logger.

    Args:
        level: The minimum severity that will be emitted. Defaults to
            :data:`logging.INFO`.
    """
    logger = logging.getLogger("student_analytics")
    logger.setLevel(level)
    # Remove any handlers attached in previous configurations.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(
        logging.Formatter(fmt=_DEFAULT_FORMAT, datefmt=_DEFAULT_DATE_FORMAT)
    )
    logger.addHandler(stream_handler)

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(_LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(fmt=_DEFAULT_FORMAT, datefmt=_DEFAULT_DATE_FORMAT)
    )
    logger.addHandler(file_handler)

    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``student_analytics`` namespace.

    Args:
        name: The suffix appended to ``student_analytics`` (e.g. ``"readers"``).

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    return logging.getLogger(f"student_analytics.{name}")
