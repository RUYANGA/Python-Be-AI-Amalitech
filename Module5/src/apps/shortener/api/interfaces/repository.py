"""Abstraction for URL persistence.

The service layer talks to this interface, not to Django's ORM. That
gives us three things: unit-testable services (swap in an in-memory
fake), a clean seam for the Redis-backed repository in Module 8, and
a documented data-access contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

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

    @abstractmethod
    def get_by_id(self, pk: int) -> URL | None:
        """Return the URL with primary key ``pk`` or ``None`` if absent."""
        raise NotImplementedError

    @abstractmethod
    def list_by_owner(self, owner) -> Iterable[URL]:
        """Return every URL owned by ``owner``."""
        raise NotImplementedError

    @abstractmethod
    def update(self, url: URL, original_url: str) -> URL:
        """Persist a new ``original_url`` for ``url`` and return it."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, url: URL) -> None:
        """Permanently remove ``url``."""
        raise NotImplementedError
