"""Celery tasks for the analytics service.

``track_click_task`` is the write-behind persistence step for a single
click event: ``ClickIngestView`` enqueues it and returns immediately,
instead of resolving geo and writing the ``Click`` row in the request
thread — so a burst of redirects on the shortener service can never back
up analytics' database writes onto the hot path.
"""

from __future__ import annotations

import logging

from celery import shared_task

from apps.analytics.api.geo import GeoIP2FastLocator
from apps.analytics.api.services.factory import build_click_repository

logger = logging.getLogger(__name__)


@shared_task(name="analytics.track_click")
def track_click_task(
    short_code: str,
    ip_address: str | None,
    user_agent: str = "",
    referer: str = "",
) -> None:
    """Resolve geo and persist a single click event for ``short_code``."""
    country = GeoIP2FastLocator().country_code(ip_address)
    repository = build_click_repository()
    repository.record_click(
        short_code,
        ip_address=ip_address,
        user_agent=user_agent,
        referer=referer,
        country=country,
    )
    logger.info("click.recorded_async short_code=%s country=%s", short_code, country)
