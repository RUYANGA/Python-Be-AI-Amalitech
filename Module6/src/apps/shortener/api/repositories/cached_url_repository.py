"""Redis-cached implementation of :class:`IURLRepository`.

Uses Redis as a read-through cache over the SQLAlchemy repository.
Write operations go directly to the database and invalidate the cache.
Read operations check Redis first, falling back to the SA repo on cache miss.

Cache key scheme:
    - ``url:code:{short_code}``  -> cached URL dict by short code
    - ``url:id:{pk}``            -> cached URL dict by primary key
    - ``url:exists:{short_code}``-> existence check result
"""

from __future__ import annotations

import logging

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
_STATS_CACHE_TTL: int = 60  # 1 minute — analytics change frequently


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
        return url

    def update(
        self,
        url: URLModel,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
    ) -> URLModel:
        updated = self._orm.update(
            url,
            original_url=original_url,
            title=title,
            tags=tags,
            expires_at=expires_at,
        )
        self._invalidate(updated.short_code, updated.id)
        return updated

    def delete(self, url: URLModel) -> None:
        self._invalidate(url.short_code, url.id)
        self._orm.delete(url)

    def get_aggregate_stats(self, url: URLModel) -> URLAggregateStats:
        cache_key = f"url:stats:{url.id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            from datetime import datetime

            return URLAggregateStats(
                total_clicks=cached["total_clicks"],
                unique_countries=cached["unique_countries"],
                top_referer=cached["top_referer"],
                last_clicked_at=(
                    datetime.fromisoformat(cached["last_clicked_at"])
                    if cached.get("last_clicked_at")
                    else None
                ),
            )
        stats = self._orm.get_aggregate_stats(url)
        self._cache.set(
            cache_key,
            {
                "total_clicks": stats.total_clicks,
                "unique_countries": stats.unique_countries,
                "top_referer": stats.top_referer,
                "last_clicked_at": (
                    stats.last_clicked_at.isoformat() if stats.last_clicked_at else None
                ),
            },
            ttl=_STATS_CACHE_TTL,
        )
        return stats

    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        return self._orm.list_with_filters(filters, limit=limit, cursor=cursor)

    def get_click_time_series(self, url: URLModel, days: int = 30) -> list[tuple[str, int]]:
        cache_key = f"url:ts:{url.id}:{days}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return [(entry["date"], entry["clicks"]) for entry in cached]
        rows = self._orm.get_click_time_series(url, days=days)
        self._cache.set(
            cache_key,
            [{"date": d, "clicks": c} for d, c in rows],
            ttl=_STATS_CACHE_TTL,
        )
        return rows

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    def invalidate(self, url: URLModel) -> None:
        """Evict all cached entries for ``url`` after external writes."""
        self._invalidate(url.short_code, url.id)
        self._cache.delete(f"url:stats:{url.id}")
        self._cache.delete(f"url:ts:{url.id}:30")
        logger.debug("cache.invalidated_external id=%s short_code=%s", url.id, url.short_code)

    def _invalidate(self, short_code: str, pk: int) -> None:
        self._cache.delete(f"url:code:{short_code}")
        self._cache.delete(f"url:id:{pk}")
        self._cache.delete(f"url:exists:{short_code}")
        logger.debug("cache.invalidated short_code=%s pk=%s", short_code, pk)

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
            "tags": [t.name for t in url.tags] if hasattr(url, "tags") and url.tags else [],
        }

    def _dict_to_url(self, data: dict) -> URLModel:
        from datetime import datetime

        from database.shortener.models import TagModel

        url = URLModel(
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
        tag_names = data.get("tags", [])
        if tag_names:
            url.tags = [TagModel(name=name) for name in tag_names]
        return url
