"""Centralised logging configuration for the Employee Payroll Tracker.

Usage (in any module)::

    from employee_payroll_tracker.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Employee created: %s", employee)
"""

import logging
import logging.handlers
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "payroll.log"

_FORMAT = "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _ensure_log_dir() -> None:
    """Create the log directory if it does not exist."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _build_console_handler() -> logging.Handler:
    """Return a console handler that logs INFO and above."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    return handler


def _build_file_handler() -> logging.Handler:
    """Return a rotating file handler that logs DEBUG and above."""
    _ensure_log_dir()
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    return handler


_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for *name*.

    The logger writes DEBUG+ to a rotating file and INFO+ to stdout.
    Each module should call ``get_logger(__name__)`` once at module
    level and reuse the returned instance.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(_build_console_handler())
    logger.addHandler(_build_file_handler())
    logger.propagate = False

    _loggers[name] = logger
    return logger
