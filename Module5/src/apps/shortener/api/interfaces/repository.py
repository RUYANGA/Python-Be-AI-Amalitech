"""Abstraction for URL persistence.

The service layer talks to this interface, not to Django's ORM. That
gives us three things: unit-testable services (swap in an in-memory
fake), a clean seam for the Redis-backed repository in Module 8, and
a documented data-access contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from apps.shortener.models import URL


class IURLRepository(ABC):
    """Read/write operations for :class:`URL` entities."""

    @abstractmethod
    def create(
        self,
        original_url: str,
        short_code: str,
        owner=None,
    ) -> URL:
        """Persist a new URL and return the saved instance."""
        raise NotImplementedError

    @abstractmethod
    def get_by_short_code(self, short_code: str) -> URL | None:
        """Return the URL for ``short_code`` or ``None`` if absent."""
        raise NotImplementedError

    @abstractmethod
    def exists_by_short_code(self, short_code: str) -> bool:
        """Return ``True`` iff a URL with ``short_code`` already exists."""
        raise NotImplementedError
