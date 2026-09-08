"""Celery Beat periodic tasks for the shortener service.

Registered via ``CELERY_BEAT_SCHEDULE`` in ``config.settings`` and run by
the ``shortener-beat``/``shortener-worker`` containers (see
``docker-compose.yml``) — never invoked from a view or the request path.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from apps.shortener.api.services.factory import build_url_service
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
