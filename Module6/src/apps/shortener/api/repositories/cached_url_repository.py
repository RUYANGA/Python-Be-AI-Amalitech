"""Redis-cached implementation of :class:`IURLRepository`.

Uses Redis as a read-through cache over the SQLAlchemy repository.
Write operations go directly to the database and invalidate the cache.
Read operations check Redis first, falling back to the SA repo on cache miss.

Cache key scheme:
    - ``url:code:{short_code}``  -> cached URL dict by short code
    - ``url:id:{pk}``            -> cached URL dict by primary key
    - ``url:exists:{short_code}``-> existence check result
    - ``url:list:{owner_id}``    -> cached list of URL IDs for an owner
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from apps.shortener.api.cache.redis_client import RedisClient, get_redis_client
from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLAggregateStats,
    URLListFilters,
)
from apps.shortener.api.repositories.url_repository import SQLAlchemyURLRepository
from database.shortener.models import URLModel

logger = logging.getLogger(__name__)

_URL_CACHE_TTL: int = 600  # 10 minutes
_EXISTS_CACHE_TTL: int = 300  # 5 minutes
_LIST_CACHE_TTL: int = 120  # 2 minutes


class CachedURLRepository(IURLRepository):
    """Decorates :class:`SQLAlchemyURLRepository` with Redis caching.

    The cache is write-through: every mutation invalidates affected keys
    so subsequent reads always reflect the latest state. On connection
    failure the repository degrades gracefully to pure SA access.
    """

    def __init__(
        self,
        orm_repository: SQLAlchemyURLRepository | None = None,
        redis_client: RedisClient | None = None,
    ) -> None:
        self._orm = orm_repository or SQLAlchemyURLRepository()
        self._cache = redis_client or get_redis_client()

    # ------------------------------------------------------------------
    # Read operations (cached)
    # ------------------------------------------------------------------

    def get_by_short_code(self, short_code: str) -> URLModel | None:
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

    def get_by_id(self, pk: int) -> URLModel | None:
        cache_key = f"url:id:{pk}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return self._dict_to_url(cached)

        logger.debug("cache.miss key=%s", cache_key)
        url = self._orm.get_by_id(pk)
        if url is not None:
            self._cache.set(cache_key, self._url_to_dict(url), ttl=_URL_CACHE_TTL)
        return url

    # ------------------------------------------------------------------
    # Write operations (invalidate cache)
    # ------------------------------------------------------------------

    def create(
        self,
        original_url: str,
        short_code: str,
        owner=None,
    ) -> URLModel:
        url = self._orm.create(original_url=original_url, short_code=short_code, owner=owner)
        self._invalidate(short_code, url.id)
        if owner is not None:
            self._cache.delete(f"url:list:{owner.id}")
        return url

    def update(self, url: URLModel, original_url: str) -> URLModel:
        updated = self._orm.update(url, original_url=original_url)
        self._invalidate(updated.short_code, updated.id)
        if updated.owner_id is not None:
            self._cache.delete(f"url:list:{updated.owner_id}")
        return updated

    def delete(self, url: URLModel) -> None:
        owner_id = url.owner_id
        self._invalidate(url.short_code, url.id)
        self._orm.delete(url)
        if owner_id is not None:
            self._cache.delete(f"url:list:{owner_id}")

    def list_by_owner(self, owner) -> Iterable[URLModel]:
        cache_key = f"url:list:{owner.id}"

        cached_ids = self._cache.get(cache_key)
        if cached_ids is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return [
                url for url in (self._get_by_id_cached(pk) for pk in cached_ids) if url is not None
            ]

        logger.debug("cache.miss key=%s", cache_key)
        urls = list(self._orm.list_by_owner(owner))
        self._cache.set(
            cache_key,
            [url.id for url in urls],
            ttl=_LIST_CACHE_TTL,
        )
        return urls

    # ------------------------------------------------------------------
    # Advanced query methods (delegate to SA repo — not cached)
    # ------------------------------------------------------------------

    def get_aggregate_stats(self, url: URLModel) -> URLAggregateStats:
        return self._orm.get_aggregate_stats(url)

    def get_top_urls(self, owner, limit: int = 10) -> list[tuple[URLModel, int]]:
        return self._orm.get_top_urls(owner, limit=limit)

    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        return self._orm.list_with_filters(filters, limit=limit, cursor=cursor)

    def get_click_time_series(self, url: URLModel, days: int = 30) -> list[tuple[str, int]]:
        return self._orm.get_click_time_series(url, days=days)

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    def _invalidate(self, short_code: str, pk: int) -> None:
        self._cache.delete(f"url:code:{short_code}")
        self._cache.delete(f"url:id:{pk}")
        self._cache.delete(f"url:exists:{short_code}")
        logger.debug("cache.invalidated short_code=%s pk=%s", short_code, pk)

    def _get_by_id_cached(self, pk: int) -> URLModel | None:
        cache_key = f"url:id:{pk}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            return self._dict_to_url(cached)

        url = self._orm.get_by_id(pk)
        if url is not None:
            self._cache.set(cache_key, self._url_to_dict(url), ttl=_URL_CACHE_TTL)
        return url

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _url_to_dict(url: URLModel) -> dict:
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
        }

    def _dict_to_url(self, data: dict) -> URLModel:
        from datetime import datetime

        return URLModel(
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
