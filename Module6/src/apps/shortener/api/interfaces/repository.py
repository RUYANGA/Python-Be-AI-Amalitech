"""Abstraction for URL persistence.

The service layer talks to this interface, not to Django's ORM. That
gives us three things: unit-testable services (swap in an in-memory
fake), a clean seam for the Redis-backed repository in Module 8, and
a documented data-access contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from database.shortener.models import URLModel


@dataclass(frozen=True)
class URLAggregateStats:
    """Aggregated statistics for a single URL."""

    total_clicks: int
    unique_countries: int
    top_referer: str
    last_clicked_at: datetime | None


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

    items: list[URLModel]
    next_cursor: str | None
    has_more: bool


class IURLRepository(ABC):
    """Read/write operations for :class:`URLModel` entities."""

    @abstractmethod
    def create(
        self,
        original_url: str,
        short_code: str,
        owner=None,
    ) -> URLModel:
        """Persist a new URL and return the saved instance."""
        raise NotImplementedError

    @abstractmethod
    def get_by_short_code(self, short_code: str) -> URLModel | None:
        """Return the URL for ``short_code`` or ``None`` if absent."""
        raise NotImplementedError

    @abstractmethod
    def exists_by_short_code(self, short_code: str) -> bool:
        """Return ``True`` iff a URL with ``short_code`` already exists."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, pk: int) -> URLModel | None:
        """Return the URL with primary key ``pk`` or ``None`` if absent."""
        raise NotImplementedError

    @abstractmethod
    def list_by_owner(self, owner) -> Iterable[URLModel]:
        """Return every URL owned by ``owner``."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        url: URLModel,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
    ) -> URLModel:
        """Apply optional partial fields to ``url`` and return it.

        Only the fields that are provided (not ``None``) are persisted;
        omitted fields are left unchanged.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, url: URLModel) -> None:
        """Permanently remove ``url``."""
        raise NotImplementedError

    # ── Advanced query methods ────────────────────────────────────────

    @abstractmethod
    def get_aggregate_stats(self, url: URLModel) -> URLAggregateStats:
        """Return click analytics aggregations for a single URL."""
        raise NotImplementedError

    @abstractmethod
    def get_top_urls(self, owner, limit: int = 10) -> list[tuple[URLModel, int]]:
        """Return top URLs by click count for ``owner`` as ``(url, clicks)`` tuples."""
        raise NotImplementedError

    @abstractmethod
    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        """Return a keyset-paginated, filtered list of URLs."""
        raise NotImplementedError

    @abstractmethod
    def get_click_time_series(self, url: URLModel, days: int = 30) -> list[tuple[str, int]]:
        """Return daily click counts as ``(YYYY-MM-DD, count)`` tuples."""
        raise NotImplementedError

    def invalidate(self, url: URLModel) -> None:  # noqa: B027
        """Invalidate all cache entries for ``url``.

        The base (non-cached) implementation is a no-op.  Cached
        repositories override this to evict stale entries after
        external writes (e.g. click recording).
        """
