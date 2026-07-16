"""Centralized logging configuration for the authentication service."""

import logging
import sys


def get_logger(name: str = "auth_service") -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: The logger name. Defaults to 'auth_service'.

    Returns:
        A configured Logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
