from __future__ import annotations

from apps.analytics.api.exceptions.base import AnalyticsError


class RepositoryError(AnalyticsError):
    """Raised when a persistence-layer operation fails.

    Wraps the underlying database exception so callers handle a domain
    exception instead of a framework or built-in ``Exception``.
    """

    def __init__(self, operation: str, **context: object) -> None:
        super().__init__(operation)
        self.operation = operation
        self.context = context
