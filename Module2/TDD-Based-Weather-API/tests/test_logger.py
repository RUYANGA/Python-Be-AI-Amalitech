"""Tests for structured logger."""

import logging

from app.logger import get_logger


def test_get_logger_returns_logger() -> None:
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


def test_get_logger_has_handler() -> None:
    logger = get_logger("test_handler")
    assert len(logger.handlers) >= 1


def test_get_logger_level() -> None:
    logger = get_logger("test_level_unique")
    assert logger.level == logging.INFO


def test_get_logger_output(capsys: object) -> None:
    logger = get_logger("test_output_unique")
    logger.info("test message")
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "[INFO]" in captured.out
    assert "test message" in captured.out
