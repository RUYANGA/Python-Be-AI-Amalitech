"""Custom exception hierarchy for the student analytics package.

A dedicated exception tree keeps error handling explicit and lets callers
distinguish between IO failures, validation failures, and unrecoverable
analytics errors without matching on messages.
"""


class AnalyticsError(Exception):
    """Base class for every error raised by the analytics package."""


class StudentDataError(AnalyticsError):
    """Raised when input student data is malformed or cannot be read."""


class InvalidGradeError(AnalyticsError):
    """Raised when a grade value is outside the valid ``[0.0, 100.0]`` range."""


class ReportWriteError(AnalyticsError):
    """Raised when an analytics report cannot be persisted to disk."""
