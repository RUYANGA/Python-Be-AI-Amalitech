"""Django ORM implementation of :class:`IClickAnalyticsRepository`.

Demonstrates Django ORM patterns for analytics:
- ``Count`` with ``values``/``annotate`` for aggregations
- ``ExtractHour`` for hourly distribution
- Atomic counter updates via ``F()`` expressions to avoid race conditions
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from django.db.models import Count, F
from django.db.models.functions import ExtractHour

from apps.shortener.api.exceptions import RepositoryError
from apps.shortener.api.interfaces.analytics import (
    CountryStats,
    HourlyDistribution,
    IClickAnalyticsRepository,
    ReferrerStats,
)
from apps.shortener.models import URL, Click

logger = logging.getLogger(__name__)


class DjangoClickAnalyticsRepository(IClickAnalyticsRepository):
    def record_click(
        self,
        url: URL,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
        country: str = "",
    ) -> None:
        """Record a click and atomically increment the counter.

        Uses Django ``F()`` expressions so the UPDATE is a single
        ``SET click_count = click_count + 1`` at the database level,
        avoiding race conditions.
        """
        try:
            Click.objects.create(
                url=url,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                country=country,
            )
            URL.objects.filter(pk=url.pk).update(
                click_count=F("click_count") + 1,
                last_accessed_at=datetime.now(UTC),
            )
            logger.info(
                "click.recorded url_id=%s ip=%s country=%s",
                url.id,
                ip_address,
                country,
            )
        except Exception as exc:
            logger.exception("click.record_failed url_id=%s", url.id)
            raise RepositoryError("record_click", url_id=url.id) from exc

    def get_country_breakdown(self, url: URL, limit: int = 10) -> list[CountryStats]:
        """Aggregate clicks by country using ``Count`` + ``values``."""
        try:
            total = Click.objects.filter(url=url).count()
            if not total:
                return []

            rows = (
                Click.objects.filter(url=url)
                .exclude(country="")
                .values("country")
                .annotate(clicks=Count("id"))
                .order_by("-clicks")[:limit]
            )

            return [
                CountryStats(
                    country=row["country"],
                    clicks=row["clicks"],
                    percentage=round(row["clicks"] / total * 100, 1),
                )
                for row in rows
            ]
        except Exception as exc:
            logger.exception("click.country_breakdown_failed url_id=%s", url.id)
            raise RepositoryError("get_country_breakdown", url_id=url.id) from exc

    def get_referrer_breakdown(self, url: URL, limit: int = 10) -> list[ReferrerStats]:
        """Aggregate clicks by referer."""
        try:
            total = Click.objects.filter(url=url).count()
            if not total:
                return []

            rows = (
                Click.objects.filter(url=url)
                .exclude(referer="")
                .values("referer")
                .annotate(clicks=Count("id"))
                .order_by("-clicks")[:limit]
            )

            return [
                ReferrerStats(
                    referer=row["referer"],
                    clicks=row["clicks"],
                    percentage=round(row["clicks"] / total * 100, 1),
                )
                for row in rows
            ]
        except Exception as exc:
            logger.exception("click.referrer_breakdown_failed url_id=%s", url.id)
            raise RepositoryError("get_referrer_breakdown", url_id=url.id) from exc

    def get_hourly_distribution(self, url: URL) -> list[HourlyDistribution]:
        """Bucket clicks by hour of day (0-23) using ``date_part``."""
        try:
            since = datetime.now(UTC) - timedelta(days=30)
            rows = (
                Click.objects.filter(url=url, clicked_at__gte=since)
                .annotate(hour=ExtractHour("clicked_at"))
                .values("hour")
                .annotate(clicks=Count("id"))
            )

            hourly_map = {
                int(row["hour"]): row["clicks"] for row in rows if row["hour"] is not None
            }
            return [HourlyDistribution(hour=h, clicks=hourly_map.get(h, 0)) for h in range(24)]
        except Exception as exc:
            logger.exception("click.hourly_distribution_failed url_id=%s", url.id)
            raise RepositoryError("get_hourly_distribution", url_id=url.id) from exc

    def get_recent_clicks(self, url: URL, limit: int = 20) -> list[dict]:
        """Return recent click records as lightweight dicts."""
        try:
            rows = Click.objects.filter(url=url).order_by("-clicked_at")[:limit]
            return [
                {
                    "id": r.id,
                    "ip_address": r.ip_address,
                    "country": r.country,
                    "referer": r.referer,
                    "clicked_at": r.clicked_at,
                }
                for r in rows
            ]
        except Exception as exc:
            logger.exception("click.recent_clicks_failed url_id=%s", url.id)
            raise RepositoryError("get_recent_clicks", url_id=url.id) from exc
