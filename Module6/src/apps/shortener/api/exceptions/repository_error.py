from __future__ import annotations

from apps.shortener.api.exceptions.base import ShortenerError


class RepositoryError(ShortenerError):
    """Raised when a persistence-layer operation fails.

    Wraps the underlying database/SQLAlchemy exception so callers handle a
    domain exception instead of a framework or built-in ``Exception``.
    """

    def __init__(self, operation: str, **context: object) -> None:
        super().__init__(operation)
        self.operation = operation
        self.context = context
