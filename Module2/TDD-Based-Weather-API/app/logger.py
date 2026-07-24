"""Structured logging for the Weather API Service."""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Get a logger that writes formatted messages to stdout.

    Output format: [LEVEL] name - message

    Args:
        name: Logger name (usually the module name).

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(name)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
