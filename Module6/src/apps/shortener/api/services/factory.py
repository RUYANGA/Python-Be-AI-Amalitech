"""Composition root for the shortener service.

Keeps the concrete-implementation choices out of the view layer so
tests can substitute doubles without patching modules.

Uses SQLAlchemy as the primary data-access layer, with Redis caching
on top and automatic fallback to plain SA if Redis is unavailable.
"""

from __future__ import annotations

import logging

from apps.shortener.api.cache.redis_client import get_redis_client
from apps.shortener.api.interfaces.analytics import IClickAnalyticsRepository
from apps.shortener.api.interfaces.repository import IURLRepository
from apps.shortener.api.repositories.analytics_repository import (
    SQLAlchemyClickAnalyticsRepository,
)
from apps.shortener.api.repositories.cached_analytics_repository import (
    CachedAnalyticsRepository,
)
from apps.shortener.api.repositories.cached_url_repository import CachedURLRepository
from apps.shortener.api.repositories.url_repository import SQLAlchemyURLRepository
from apps.shortener.api.services.short_code_generator import Base62ShortCodeGenerator
from apps.shortener.api.services.url_service import URLShortenerService

logger = logging.getLogger(__name__)


def build_url_service() -> URLShortenerService:
    """Return a fully wired :class:`URLShortenerService`.

    Falls back to plain SA repositories if Redis is unreachable,
    ensuring the service always works even without caching.
    """
    sa_repo = SQLAlchemyURLRepository()
    repository: IURLRepository | CachedURLRepository | SQLAlchemyURLRepository = sa_repo
    sa_analytics = SQLAlchemyClickAnalyticsRepository()
    analytics_repo: (
        IClickAnalyticsRepository | CachedAnalyticsRepository | SQLAlchemyClickAnalyticsRepository
    ) = sa_analytics

    try:
        redis_client = get_redis_client()
        logger.info("url_service.redis_url=%s", redis_client._url)
        if redis_client.ping():
            repository = CachedURLRepository(
                orm_repository=sa_repo,
                redis_client=redis_client,
            )
            analytics_repo = CachedAnalyticsRepository(
                orm_repository=sa_analytics,
                redis_client=redis_client,
            )
            logger.info("url_service.using_cached_repository")
        else:
            logger.warning(
                "url_service.redis_ping_failed falling_back_to_sa url=%s",
                redis_client._url,
            )
    except Exception as exc:
        logger.warning("url_service.redis_init_failed falling_back_to_sa error=%s", exc)

    return URLShortenerService(
        repository=repository,
        generator=Base62ShortCodeGenerator(),
        analytics_repository=analytics_repo,
    )
