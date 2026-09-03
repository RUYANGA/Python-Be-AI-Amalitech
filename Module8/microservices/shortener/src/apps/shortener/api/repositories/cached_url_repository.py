"""Redis-cached implementation of :class:`IURLRepository`.

Uses Redis as a read-through cache over the Django ORM repository.
Write operations go directly to the database and invalidate the cache.
Read operations check Redis first, falling back to the ORM repo on cache miss.

Cache key scheme:
    - ``url:code:{short_code}``       -> cached URL dict by short code
    - ``url:id:{pk}``                 -> cached URL dict by primary key
    - ``url:exists:{short_code}``     -> existence check result
    - ``url:list:{owner_id}:{hash}``  -> cached page of ``list_with_filters``,
      keyed by a hash of the filter/limit/cursor signature so distinct
      queries never collide
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime

from apps.shortener.api.cache.redis_client import RedisClient, get_redis_client
from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLListFilters,
)
from apps.shortener.api.repositories.url_repository import DjangoURLRepository
from apps.shortener.models import URL

logger = logging.getLogger(__name__)

_URL_CACHE_TTL: int = 600  # 10 minutes
_EXISTS_CACHE_TTL: int = 300  # 5 minutes
_LIST_CACHE_TTL: int = 30  # short — keyset pages are sensitive to inserts/deletes


class CachedURLRepository(IURLRepository):
    """Decorates :class:`DjangoURLRepository` with Redis caching.

    The cache is write-through: every mutation invalidates affected keys
    so subsequent reads always reflect the latest state. On connection
    failure the repository degrades gracefully to pure ORM access.
    """

    def __init__(
        self,
        orm_repository: DjangoURLRepository | None = None,
        redis_client: RedisClient | None = None,
    ) -> None:
        self._orm = orm_repository or DjangoURLRepository()
        self._cache = redis_client or get_redis_client()

    # ------------------------------------------------------------------
    # Read operations (cached)
    # ------------------------------------------------------------------

    def get_by_short_code(self, short_code: str) -> URL | None:
        cache_key = f"url:code:{short_code}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return self._dict_to_url(cached)

        logger.debug("cache.miss key=%s", cache_key)
        url = self._orm.get_by_short_code(short_code)
        if url is not None:
            self._cache.set(cache_key, self._url_to_dict(url), ttl=_URL_CACHE_TTL)
        return url

    def exists_by_short_code(self, short_code: str) -> bool:
        cache_key = f"url:exists:{short_code}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            return bool(cached)

        result = self._orm.exists_by_short_code(short_code)
        self._cache.set(cache_key, result, ttl=_EXISTS_CACHE_TTL)
        return result

    # ------------------------------------------------------------------
    # Write operations (invalidate cache)
    # ------------------------------------------------------------------

    def create(
        self,
        original_url: str,
        short_code: str,
        owner_id: int | None = None,
    ) -> URL:
        url = self._orm.create(original_url=original_url, short_code=short_code, owner_id=owner_id)
        self._invalidate(short_code, url.id, url.owner_id)
        return url

    def update(
        self,
        url: URL,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
        is_active: bool | None = None,
    ) -> URL:
        updated = self._orm.update(
            url,
            original_url=original_url,
            title=title,
            tags=tags,
            expires_at=expires_at,
            is_active=is_active,
        )
        self._invalidate(updated.short_code, updated.id, updated.owner_id)
        return updated

    def delete(self, url: URL) -> None:
        self._invalidate(url.short_code, url.id, url.owner_id)
        self._orm.delete(url)

    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        cache_key = self._list_cache_key(filters, limit, cursor)

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return KeysetPage(
                items=[self._dict_to_url(item) for item in cached["items"]],
                next_cursor=cached["next_cursor"],
                has_more=cached["has_more"],
            )

        logger.debug("cache.miss key=%s", cache_key)
        page = self._orm.list_with_filters(filters, limit=limit, cursor=cursor)
        self._cache.set(
            cache_key,
            {
                "items": [self._url_to_dict(url) for url in page.items],
                "next_cursor": page.next_cursor,
                "has_more": page.has_more,
            },
            ttl=_LIST_CACHE_TTL,
        )
        return page

    def count_active_by_owner(self, owner_id: int) -> int:
        # Not cached: this backs a tier quota check, where a stale count
        # could let a free user slip past the limit or be wrongly blocked
        # right after freeing up a slot.
        return self._orm.count_active_by_owner(owner_id)

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    def invalidate(self, url: URL) -> None:
        """Evict all cached entries for ``url`` after external writes."""
        self._invalidate(url.short_code, url.id, url.owner_id)
        logger.debug("cache.invalidated_external id=%s short_code=%s", url.id, url.short_code)

    def _invalidate(self, short_code: str, pk: int, owner_id: int | None = None) -> None:
        self._cache.delete(f"url:code:{short_code}")
        self._cache.delete(f"url:id:{pk}")
        self._cache.delete(f"url:exists:{short_code}")
        removed = self._cache.flush_pattern(f"url:list:{owner_id}:*") if owner_id is not None else 0
        logger.debug(
            "cache.invalidated short_code=%s pk=%s owner_id=%s list_removed=%d",
            short_code,
            pk,
            owner_id,
            removed,
        )

    @staticmethod
    def _list_cache_key(filters: URLListFilters, limit: int, cursor: str | None) -> str:
        signature = {
            "search": filters.search,
            "is_active": filters.is_active,
            "tag": filters.tag,
            "created_after": filters.created_after.isoformat() if filters.created_after else None,
            "created_before": (
                filters.created_before.isoformat() if filters.created_before else None
            ),
            "min_clicks": filters.min_clicks,
            "max_clicks": filters.max_clicks,
            "ordering": filters.ordering,
            "limit": limit,
            "cursor": cursor,
        }
        digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
        return f"url:list:{filters.owner_id}:{digest}"

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _url_to_dict(url: URL) -> dict:
        try:
            tags = [t.name for t in url.tags.all()] if hasattr(url, "tags") else []
        except Exception:
            tags = []
        return {
            "id": url.id,
            "original_url": url.original_url,
            "short_code": url.short_code,
            "title": url.title,
            "owner_id": url.owner_id,
            "click_count": url.click_count,
            "is_active": url.is_active,
            "expires_at": url.expires_at.isoformat() if url.expires_at else None,
            "last_accessed_at": url.last_accessed_at.isoformat() if url.last_accessed_at else None,
            "created_at": url.created_at.isoformat(),
            "updated_at": url.updated_at.isoformat(),
            "tags": tags,
        }

    @staticmethod
    def _dict_to_url(data: dict) -> URL:
        url = URL(
            id=data["id"],
            original_url=data["original_url"],
            short_code=data["short_code"],
            title=data.get("title", ""),
            owner_id=data.get("owner_id"),
            click_count=data.get("click_count", 0),
            is_active=data.get("is_active", True),
            expires_at=(
                datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
            ),
            last_accessed_at=(
                datetime.fromisoformat(data["last_accessed_at"])
                if data.get("last_accessed_at")
                else None
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
        return url
