"""Composition root for the url-preview service.

Keeps the concrete-implementation choices out of the view layer so
tests can substitute doubles without patching modules.
"""

from __future__ import annotations

from django.conf import settings

from apps.preview.api.cache.redis_client import get_redis_client
from apps.preview.api.services.circuit_breaker import DomainCircuitBreaker
from apps.preview.api.services.html_preview_fetcher import HTMLPreviewFetcher
from apps.preview.api.services.preview_service import PreviewService


def build_preview_service() -> PreviewService:
    """Return a fully wired :class:`PreviewService`."""
    redis_client = get_redis_client()
    breaker = DomainCircuitBreaker(
        redis_client=redis_client,
        failure_threshold=settings.PREVIEW_CIRCUIT_FAILURE_THRESHOLD,
        open_seconds=settings.PREVIEW_CIRCUIT_OPEN_SECONDS,
    )
    return PreviewService(
        fetcher=HTMLPreviewFetcher(),
        breaker=breaker,
        cache=redis_client,
        max_attempts=settings.PREVIEW_MAX_ATTEMPTS,
        base_delay=settings.PREVIEW_RETRY_BASE_DELAY,
        cache_ttl=settings.PREVIEW_CACHE_TTL,
    )
