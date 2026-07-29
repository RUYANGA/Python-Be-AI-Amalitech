"""Tests for :mod:`student_analytics.logger`."""

import logging

from student_analytics.logger import configure_logging, get_logger


def test_configure_logging_attaches_two_handlers() -> None:
    configure_logging(level=logging.DEBUG)
    logger = logging.getLogger("student_analytics")
    assert len(logger.handlers) == 2
    assert logger.level == logging.DEBUG


def test_configure_logging_replaces_previous_handlers() -> None:
    configure_logging(level=logging.INFO)
    configure_logging(level=logging.WARNING)
    logger = logging.getLogger("student_analytics")
    # Even after two calls, exactly two handlers remain attached.
    assert len(logger.handlers) == 2
    assert logger.level == logging.WARNING


def test_get_logger_returns_child_of_package_logger() -> None:
    child = get_logger("readers")
    assert child.name == "student_analytics.readers"


def test_child_logger_emits_to_package_handler() -> None:
    """Child loggers route through the package handler, not the root logger."""
    configure_logging(level=logging.INFO)
    child = get_logger("test_emit")
    # The child must be a descendant of the package logger.
    assert child.name.startswith("student_analytics.")
    # propagate=False on the package logger means records stop there.
    package_logger = logging.getLogger("student_analytics")
    assert package_logger.propagate is False
    # One handler is a StreamHandler, the other is a FileHandler.
    assert len(package_logger.handlers) == 2
    handler_types = {type(handler) for handler in package_logger.handlers}
    assert logging.StreamHandler in handler_types
    assert logging.FileHandler in handler_types


def test_file_handler_writes_to_log_dir() -> None:
    """The file handler targets the ``logs/`` directory."""
    configure_logging(level=logging.DEBUG)
    logger = logging.getLogger("student_analytics")
    file_handlers = [
        handler
        for handler in logger.handlers
        if isinstance(handler, logging.FileHandler)
    ]
    assert len(file_handlers) == 1
    handler = file_handlers[0]
    assert "logs" in handler.baseFilename
    assert handler.mode == "a"
