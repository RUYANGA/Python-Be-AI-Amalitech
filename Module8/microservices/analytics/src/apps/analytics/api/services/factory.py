"""Composition root for the analytics service.

Falls back to plain ORM access if Redis is unreachable, ensuring the
analytics endpoint and click ingestion always work even without
caching.
"""

from __future__ import annotations

import logging

from apps.analytics.api.cache.redis_client import get_redis_client
from apps.analytics.api.interfaces.analytics import IClickAnalyticsRepository
from apps.analytics.api.repositories.analytics_repository import DjangoClickAnalyticsRepository
from apps.analytics.api.repositories.cached_analytics_repository import (
    CachedClickAnalyticsRepository,
)
from apps.analytics.api.services.analytics_service import AnalyticsService
from apps.analytics.api.services.url_ownership_client import URLOwnershipClient

logger = logging.getLogger(__name__)


def build_click_repository() -> IClickAnalyticsRepository:
    """Return the click-analytics repository, cached behind Redis when reachable.

    Shared by both the analytics read endpoint and the click-ingest
    write path, so a recorded click invalidates the same cache the next
    read will check.
    """
    orm_repo = DjangoClickAnalyticsRepository()
    repository: IClickAnalyticsRepository = orm_repo

    try:
        redis_client = get_redis_client()
        if redis_client.ping():
            repository = CachedClickAnalyticsRepository(
                orm_repository=orm_repo, redis_client=redis_client
            )
            logger.info("analytics_repository.using_cached_repository")
        else:
            logger.warning(
                "analytics_repository.redis_ping_failed falling_back_to_orm url=%s",
                redis_client._url,
            )
    except Exception as exc:
        logger.warning("analytics_repository.redis_init_failed falling_back_to_orm error=%s", exc)

    return repository


def build_analytics_service() -> AnalyticsService:
    return AnalyticsService(
        repository=build_click_repository(),
        ownership_client=URLOwnershipClient(),
    )
