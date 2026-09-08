"""Celery Beat periodic tasks for the shortener service.

Registered via ``CELERY_BEAT_SCHEDULE`` in ``config.settings`` and run by
the ``shortener-beat``/``shortener-worker`` containers (see
``docker-compose.yml``) — never invoked from a view or the request path.
"""

from __future__ import annotations

import logging

import requests
from celery import shared_task
from django.utils import timezone

from apps.shortener.api.services.factory import build_url_service
from apps.shortener.api.services.preview_client import PreviewClient
from apps.shortener.models import URL

logger = logging.getLogger(__name__)


@shared_task(name="shortener.archive_expired_urls")
def archive_expired_urls_task() -> int:
    """Deactivate every active URL whose ``expires_at`` has passed.

    Runs nightly (see ``CELERY_BEAT_SCHEDULE``). Goes through
    :func:`build_url_service` rather than a bulk ``QuerySet.update()`` so
    each archived URL's cache entry is invalidated the same way a manual
    edit would invalidate it — a stale ``url:code:*`` entry would keep
    redirecting past expiry otherwise. Returns the number archived.
    """
    service = build_url_service()
    now = timezone.now()
    expired_ids = list(
        URL.objects.filter(
            is_active=True,
            expires_at__isnull=False,
            expires_at__lte=now,
        ).values_list("id", flat=True)
    )

    archived = 0
    for url_id in expired_ids:
        url = URL.objects.filter(pk=url_id).first()
        if url is None:
            continue
        service.update(url, is_active=False)
        archived += 1

    logger.info("url.archive_expired_completed count=%d", archived)
    return archived


@shared_task(
    name="shortener.fetch_url_preview",
    autoretry_for=(requests.ConnectionError, requests.Timeout),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_kwargs={"max_retries": 3},
)
def fetch_url_preview_task(url_id: int, original_url: str) -> bool:
    """Fetch and backfill title/description/favicon for a newly created URL.

    Dispatched fire-and-forget from ``URLCreateMixin.post`` right after a URL
    is created — never inline with the create request. Retries (via
    ``autoretry_for``) only cover this task's own hop to the url-preview
    service being briefly unreachable; the destination-site fetch itself
    already has its own retry-with-backoff and circuit breaker *inside*
    url-preview (see ``url-preview/README.md``), so a definitive failure
    from there (``PreviewClient.fetch`` returning ``None``) is not retried
    again here — it just means the preview fields stay blank. Returns
    ``True`` iff the fields were actually updated.
    """
    result = PreviewClient().fetch(original_url)
    if result is None:
        logger.warning("url.preview_unavailable id=%s url=%s", url_id, original_url)
        return False

    url = URL.objects.filter(pk=url_id).first()
    if url is None:
        logger.warning("url.preview_target_missing id=%s", url_id)
        return False

    service = build_url_service()
    service.update(
        url,
        title=result.title if not url.title else None,
        description=result.description or None,
        favicon_url=result.favicon_url or None,
    )
    logger.info("url.preview_fetched id=%s short_code=%s", url.id, url.short_code)
    return True
