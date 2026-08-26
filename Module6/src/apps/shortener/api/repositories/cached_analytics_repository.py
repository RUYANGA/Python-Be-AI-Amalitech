"""Redis-cached implementation of :class:`IClickAnalyticsRepository`.

Decorates the SQLAlchemy analytics repository with Redis caching for
expensive aggregation queries.  Write operations (``record_click``)
always hit the database and invalidate related URL cache keys.
"""

from __future__ import annotations

import logging

from apps.shortener.api.cache.redis_client import RedisClient, get_redis_client
from apps.shortener.api.interfaces.analytics import (
    CountryStats,
    HourlyDistribution,
    IClickAnalyticsRepository,
    ReferrerStats,
)
from apps.shortener.api.repositories.analytics_repository import (
    SQLAlchemyClickAnalyticsRepository,
)
from database.shortener.models import URLModel

logger = logging.getLogger(__name__)

_ANALYTICS_CACHE_TTL: int = 30  # 30 seconds — analytics change fast


class CachedAnalyticsRepository(IClickAnalyticsRepository):
    """Decorates :class:`SQLAlchemyClickAnalyticsRepository` with Redis caching.

    Only read methods are cached.  ``record_click`` writes through to
    the database and invalidates URL entity cache keys so the
    ``CachedURLRepository`` evicts stale ``click_count`` values.
    """

    def __init__(
        self,
        orm_repository: SQLAlchemyClickAnalyticsRepository | None = None,
        redis_client: RedisClient | None = None,
    ) -> None:
        self._orm = orm_repository or SQLAlchemyClickAnalyticsRepository()
        self._cache = redis_client or get_redis_client()

    # ------------------------------------------------------------------
    # Write (no caching — always hits DB, invalidates URL cache)
    # ------------------------------------------------------------------

    def record_click(
        self,
        url: URLModel,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
        country: str = "",
    ) -> None:
        self._orm.record_click(
            url,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            country=country,
        )
        self._invalidate_analytics(url.id)

    # ------------------------------------------------------------------
    # Read (cached with short TTL)
    # ------------------------------------------------------------------

    def get_country_breakdown(self, url: URLModel, limit: int = 10) -> list[CountryStats]:
        cache_key = f"analytics:countries:{url.id}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return [CountryStats(**entry) for entry in cached]
        result = self._orm.get_country_breakdown(url, limit=limit)
        self._cache.set(
            cache_key,
            [
                {"country": s.country, "clicks": s.clicks, "percentage": s.percentage}
                for s in result
            ],
            ttl=_ANALYTICS_CACHE_TTL,
        )
        return result

    def get_referrer_breakdown(self, url: URLModel, limit: int = 10) -> list[ReferrerStats]:
        cache_key = f"analytics:referrers:{url.id}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return [ReferrerStats(**entry) for entry in cached]
        result = self._orm.get_referrer_breakdown(url, limit=limit)
        self._cache.set(
            cache_key,
            [
                {"referer": s.referer, "clicks": s.clicks, "percentage": s.percentage}
                for s in result
            ],
            ttl=_ANALYTICS_CACHE_TTL,
        )
        return result

    def get_hourly_distribution(self, url: URLModel) -> list[HourlyDistribution]:
        cache_key = f"analytics:hourly:{url.id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return [HourlyDistribution(**entry) for entry in cached]
        result = self._orm.get_hourly_distribution(url)
        self._cache.set(
            cache_key,
            [{"hour": h.hour, "clicks": h.clicks} for h in result],
            ttl=_ANALYTICS_CACHE_TTL,
        )
        return result

    def get_recent_clicks(self, url: URLModel, limit: int = 20) -> list[dict]:
        return self._orm.get_recent_clicks(url, limit=limit)

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    def _invalidate_analytics(self, url_id: int) -> None:
        self._cache.flush_pattern(f"analytics:*:{url_id}:*")
        self._cache.flush_pattern(f"analytics:hourly:{url_id}")
        self._cache.delete(f"url:stats:{url_id}")
        logger.debug("analytics.cache.invalidated url_id=%s", url_id)
