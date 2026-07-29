"""Tests for :mod:`student_analytics.exceptions`."""

from __future__ import annotations

from student_analytics.exceptions import (
    AnalyticsError,
    InvalidGradeError,
    ReportWriteError,
    StudentDataError,
)


def test_all_exceptions_inherit_from_analytics_error() -> None:
    for exc_cls in (StudentDataError, InvalidGradeError, ReportWriteError):
        assert issubclass(exc_cls, AnalyticsError)


def test_analytics_error_is_an_exception() -> None:
    assert issubclass(AnalyticsError, Exception)


def test_exceptions_carry_message() -> None:
    error = StudentDataError("boom")
    assert str(error) == "boom"
