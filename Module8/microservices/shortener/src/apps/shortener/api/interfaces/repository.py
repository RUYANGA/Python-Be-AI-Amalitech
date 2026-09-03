"""Abstraction for URL persistence.

The service layer talks to this interface, not to Django's ORM. That
gives us unit-testable services (swap in an in-memory fake) and a
documented data-access contract.

Click analytics no longer live here — that's the analytics service's
own repository, over its own database.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from apps.shortener.models import URL


@dataclass(frozen=True)
class URLListFilters:
    """Dynamic filter parameters for URL listing."""

    search: str | None = None
    is_active: bool | None = None
    tag: str | None = None
    owner_id: int | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    min_clicks: int | None = None
    max_clicks: int | None = None
    ordering: str = "-created_at"


@dataclass(frozen=True)
class KeysetPage:
    """A page of results using keyset pagination."""

    items: list[URL]
    next_cursor: str | None
    has_more: bool


class IURLRepository(ABC):
    """Read/write operations for :class:`URL` entities."""

    @abstractmethod
    def create(
        self,
        original_url: str,
        short_code: str,
        owner_id: int | None = None,
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
    def update(
        self,
        url: URL,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
    ) -> URL:
        """Apply optional partial fields to ``url`` and return it.

        Only the fields that are provided (not ``None``) are persisted;
        omitted fields are left unchanged.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, url: URL) -> None:
        """Permanently remove ``url``."""
        raise NotImplementedError

    @abstractmethod
    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        """Return a keyset-paginated, filtered list of URLs."""
        raise NotImplementedError

    @abstractmethod
    def count_active_by_owner(self, owner_id: int) -> int:
        """Return how many active URLs ``owner_id`` currently has."""
        raise NotImplementedError

    def invalidate(self, url: URL) -> None:  # noqa: B027
        """Invalidate all cache entries for ``url``.

        The base (non-cached) implementation is a no-op. Cached
        repositories override this to evict stale entries after
        external writes.
        """
