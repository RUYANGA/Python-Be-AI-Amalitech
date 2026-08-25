"""Redis-cached implementation of :class:`IURLRepository`.

Uses Redis as a read-through cache over the Django ORM repository.
Write operations go directly to the database and invalidate the cache.
Read operations check Redis first, falling back to the ORM on cache miss.

Cache key scheme:
    - ``url:code:{short_code}`` → cached URL dict by short code
    - ``url:id:{pk}``           → cached URL dict by primary key
    - ``url:exists:{short_code}`` → existence check result
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from apps.shortener.api.cache.redis_client import RedisClient, get_redis_client
from apps.shortener.api.interfaces.repository import IURLRepository
from apps.shortener.api.repositories.url_repository import DjangoURLRepository
from apps.shortener.models import URL

logger = logging.getLogger(__name__)

_URL_CACHE_TTL: int = 600  # 10 minutes
_EXISTS_CACHE_TTL: int = 300  # 5 minutes


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

    def get_by_id(self, pk: int) -> URL | None:
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
    ) -> URL:
        url = self._orm.create(original_url=original_url, short_code=short_code, owner=owner)
        self._invalidate(short_code, url.pk)
        return url

    def update(self, url: URL, original_url: str) -> URL:
        updated = self._orm.update(url, original_url=original_url)
        self._invalidate(updated.short_code, updated.pk)
        return updated

    def delete(self, url: URL) -> None:
        self._invalidate(url.short_code, url.pk)
        self._orm.delete(url)

    def list_by_owner(self, owner) -> Iterable[URL]:
        return self._orm.list_by_owner(owner)

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    def _invalidate(self, short_code: str, pk: int) -> None:
        """Remove all cached entries for a given URL."""
        self._cache.delete(f"url:code:{short_code}")
        self._cache.delete(f"url:id:{pk}")
        self._cache.delete(f"url:exists:{short_code}")
        logger.debug("cache.invalidated short_code=%s pk=%s", short_code, pk)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _url_to_dict(url: URL) -> dict:
        return {
            "pk": url.pk,
            "original_url": url.original_url,
            "short_code": url.short_code,
            "owner_id": url.owner_id,
            "created_at": url.created_at.isoformat(),
        }

    def _dict_to_url(self, data: dict) -> URL:
        return URL(
            pk=data["pk"],
            original_url=data["original_url"],
            short_code=data["short_code"],
            owner_id=data.get("owner_id"),
            created_at=data["created_at"],
        )
