"""Tests for the logging configuration."""

import logging

from app.logger import get_logger


class TestLogger:
    """Tests for the logger utility."""

    def test_get_logger_returns_logger(self) -> None:
        """get_logger should return a Logger instance."""
        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self) -> None:
        """Logger should have the requested name."""
        logger = get_logger("my_service")

        assert logger.name == "my_service"

    def test_logger_default_name(self) -> None:
        """Default logger name should be 'auth_service'."""
        logger = get_logger()

        assert logger.name == "auth_service"

    def test_logger_has_handler(self) -> None:
        """Logger should have at least one handler."""
        logger = get_logger("test_handlers")

        assert len(logger.handlers) > 0

    def test_logger_level_is_info(self) -> None:
        """Logger should be set to INFO level."""
        logger = get_logger("test_level")

        assert logger.level == logging.INFO

    def test_logger_does_not_propagate(self) -> None:
        """Logger should not propagate to root logger."""
        logger = get_logger("test_no_prop")

        assert logger.propagate is False

    def test_same_logger_returned(self) -> None:
        """Calling get_logger with same name returns same instance."""
        logger1 = get_logger("singleton_test")
        logger2 = get_logger("singleton_test")

        assert logger1 is logger2
