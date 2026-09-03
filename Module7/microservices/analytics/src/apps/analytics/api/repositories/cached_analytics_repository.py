"""Redis-cached implementation of :class:`IClickAnalyticsRepository`.

Uses Redis as a read-through cache over the Django ORM repository for
the analytics endpoint's aggregate queries (time-series, geo, referrer,
and hourly breakdowns — all recomputed from the ``clicks`` table on
every request otherwise). Writes go straight to the database and then
invalidate every cached entry for that short code, so the next read
always recomputes against fresh data.

Cache key scheme (all scoped under one short code so a single write
invalidates them together):
    - ``analytics:{short_code}:stats``               -> aggregate stats
    - ``analytics:{short_code}:countries:{limit}``    -> country breakdown
    - ``analytics:{short_code}:referrers:{limit}``    -> referrer breakdown
    - ``analytics:{short_code}:hourly``               -> hourly distribution
    - ``analytics:{short_code}:recent:{limit}``       -> recent clicks
    - ``analytics:{short_code}:timeseries:{days}``    -> daily time series
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime

from apps.analytics.api.cache.redis_client import RedisClient, get_redis_client
from apps.analytics.api.interfaces.analytics import (
    CountryStats,
    HourlyDistribution,
    IClickAnalyticsRepository,
    ReferrerStats,
    URLAggregateStats,
)
from apps.analytics.api.repositories.analytics_repository import DjangoClickAnalyticsRepository

logger = logging.getLogger(__name__)

_STATS_CACHE_TTL: int = 120  # 2 minutes — a safety net; writes invalidate directly


class CachedClickAnalyticsRepository(IClickAnalyticsRepository):
    """Decorates :class:`DjangoClickAnalyticsRepository` with Redis caching.

    Read-through, write-invalidate: :meth:`record_click` flushes every
    cached entry for that short code so the next read recomputes from
    the database. On connection failure the repository degrades
    gracefully to pure ORM access.
    """

    def __init__(
        self,
        orm_repository: DjangoClickAnalyticsRepository | None = None,
        redis_client: RedisClient | None = None,
    ) -> None:
        self._orm = orm_repository or DjangoClickAnalyticsRepository()
        self._cache = redis_client or get_redis_client()

    # ------------------------------------------------------------------
    # Write operations (invalidate cache)
    # ------------------------------------------------------------------

    def record_click(
        self,
        short_code: str,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
        country: str = "",
        city: str = "",
    ) -> None:
        self._orm.record_click(
            short_code,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            country=country,
            city=city,
        )
        removed = self._cache.flush_pattern(f"analytics:{short_code}:*")
        logger.debug("analytics_cache.invalidated short_code=%s removed=%d", short_code, removed)

    # ------------------------------------------------------------------
    # Read operations (cached)
    # ------------------------------------------------------------------

    def get_aggregate_stats(self, short_code: str) -> URLAggregateStats:
        cache_key = f"analytics:{short_code}:stats"

        cached: dict = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return URLAggregateStats(
                total_clicks=cached["total_clicks"],
                unique_countries=cached["unique_countries"],
                top_referer=cached["top_referer"],
                last_clicked_at=(
                    datetime.fromisoformat(cached["last_clicked_at"])
                    if cached["last_clicked_at"]
                    else None
                ),
            )

        logger.debug("cache.miss key=%s", cache_key)
        stats = self._orm.get_aggregate_stats(short_code)
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

    def get_country_breakdown(self, short_code: str, limit: int = 10) -> list[CountryStats]:
        cache_key = f"analytics:{short_code}:countries:{limit}"

        cached: list[dict] = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return [CountryStats(**row) for row in cached]

        logger.debug("cache.miss key=%s", cache_key)
        breakdown = self._orm.get_country_breakdown(short_code, limit=limit)
        self._cache.set(cache_key, [asdict(row) for row in breakdown], ttl=_STATS_CACHE_TTL)
        return breakdown

    def get_referrer_breakdown(self, short_code: str, limit: int = 10) -> list[ReferrerStats]:
        cache_key = f"analytics:{short_code}:referrers:{limit}"

        cached: list[dict] = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return [ReferrerStats(**row) for row in cached]

        logger.debug("cache.miss key=%s", cache_key)
        breakdown = self._orm.get_referrer_breakdown(short_code, limit=limit)
        self._cache.set(cache_key, [asdict(row) for row in breakdown], ttl=_STATS_CACHE_TTL)
        return breakdown

    def get_hourly_distribution(self, short_code: str) -> list[HourlyDistribution]:
        cache_key = f"analytics:{short_code}:hourly"

        cached: list[dict] = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return [HourlyDistribution(**row) for row in cached]

        logger.debug("cache.miss key=%s", cache_key)
        distribution = self._orm.get_hourly_distribution(short_code)
        self._cache.set(cache_key, [asdict(row) for row in distribution], ttl=_STATS_CACHE_TTL)
        return distribution

    def get_recent_clicks(self, short_code: str, limit: int = 20) -> list[dict]:
        cache_key = f"analytics:{short_code}:recent:{limit}"

        cached: list[dict] = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return [
                {**row, "clicked_at": datetime.fromisoformat(row["clicked_at"])} for row in cached
            ]

        logger.debug("cache.miss key=%s", cache_key)
        clicks = self._orm.get_recent_clicks(short_code, limit=limit)
        self._cache.set(
            cache_key,
            [{**row, "clicked_at": row["clicked_at"].isoformat()} for row in clicks],
            ttl=_STATS_CACHE_TTL,
        )
        return clicks

    def get_click_time_series(self, short_code: str, days: int = 30) -> list[tuple[str, int]]:
        cache_key = f"analytics:{short_code}:timeseries:{days}"

        cached: list[list] = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("cache.hit key=%s", cache_key)
            return [tuple(row) for row in cached]

        logger.debug("cache.miss key=%s", cache_key)
        series = self._orm.get_click_time_series(short_code, days=days)
        self._cache.set(cache_key, [list(row) for row in series], ttl=_STATS_CACHE_TTL)
        return series
