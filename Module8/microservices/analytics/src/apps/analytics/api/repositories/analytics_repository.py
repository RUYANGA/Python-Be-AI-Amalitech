"""Django ORM implementation of :class:`IClickAnalyticsRepository`.

Everything is keyed by ``short_code`` (a plain string) rather than a
foreign key to a URL row — that row belongs to the shortener service's
own database, which this service never queries directly.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from django.db.models import Count, Max
from django.db.models.functions import ExtractHour, TruncDay

from apps.analytics.api.exceptions import RepositoryError
from apps.analytics.api.interfaces.analytics import (
    CountryStats,
    HourlyDistribution,
    IClickAnalyticsRepository,
    ReferrerStats,
    URLAggregateStats,
)
from apps.analytics.models import Click

logger = logging.getLogger(__name__)


class DjangoClickAnalyticsRepository(IClickAnalyticsRepository):
    def record_click(
        self,
        short_code: str,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
        country: str = "",
        city: str = "",
    ) -> None:
        try:
            Click.objects.create(
                short_code=short_code,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                country=country,
                city=city,
            )
            logger.info(
                "click.recorded short_code=%s ip=%s country=%s", short_code, ip_address, country
            )
        except Exception as exc:
            logger.exception("click.record_failed short_code=%s", short_code)
            raise RepositoryError("record_click", short_code=short_code) from exc

    def get_aggregate_stats(self, short_code: str) -> URLAggregateStats:
        try:
            clicks = Click.objects.filter(short_code=short_code)
            total_clicks = clicks.count()
            unique_countries = clicks.exclude(country="").values("country").distinct().count()
            last_clicked_at = clicks.aggregate(max=Max("clicked_at"))["max"]
            top_referer_row = (
                clicks.exclude(referer="")
                .values("referer")
                .annotate(cnt=Count("id"))
                .order_by("-cnt")
                .first()
            )
            return URLAggregateStats(
                total_clicks=total_clicks,
                unique_countries=unique_countries,
                top_referer=top_referer_row["referer"] if top_referer_row else "",
                last_clicked_at=last_clicked_at,
            )
        except Exception as exc:
            logger.exception("click.aggregate_stats_failed short_code=%s", short_code)
            raise RepositoryError("get_aggregate_stats", short_code=short_code) from exc

    def get_country_breakdown(self, short_code: str, limit: int = 10) -> list[CountryStats]:
        try:
            total = Click.objects.filter(short_code=short_code).count()
            if not total:
                return []
            rows = (
                Click.objects.filter(short_code=short_code)
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
            logger.exception("click.country_breakdown_failed short_code=%s", short_code)
            raise RepositoryError("get_country_breakdown", short_code=short_code) from exc

    def get_referrer_breakdown(self, short_code: str, limit: int = 10) -> list[ReferrerStats]:
        try:
            total = Click.objects.filter(short_code=short_code).count()
            if not total:
                return []
            rows = (
                Click.objects.filter(short_code=short_code)
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
            logger.exception("click.referrer_breakdown_failed short_code=%s", short_code)
            raise RepositoryError("get_referrer_breakdown", short_code=short_code) from exc

    def get_hourly_distribution(self, short_code: str) -> list[HourlyDistribution]:
        try:
            since = datetime.now(UTC) - timedelta(days=30)
            rows = (
                Click.objects.filter(short_code=short_code, clicked_at__gte=since)
                .annotate(hour=ExtractHour("clicked_at"))
                .values("hour")
                .annotate(clicks=Count("id"))
            )
            hourly_map = {
                int(row["hour"]): row["clicks"] for row in rows if row["hour"] is not None
            }
            return [HourlyDistribution(hour=h, clicks=hourly_map.get(h, 0)) for h in range(24)]
        except Exception as exc:
            logger.exception("click.hourly_distribution_failed short_code=%s", short_code)
            raise RepositoryError("get_hourly_distribution", short_code=short_code) from exc

    def get_recent_clicks(self, short_code: str, limit: int = 20) -> list[dict]:
        try:
            rows = Click.objects.filter(short_code=short_code).order_by("-clicked_at")[:limit]
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
            logger.exception("click.recent_clicks_failed short_code=%s", short_code)
            raise RepositoryError("get_recent_clicks", short_code=short_code) from exc

    def get_click_time_series(self, short_code: str, days: int = 30) -> list[tuple[str, int]]:
        since = datetime.now(UTC) - timedelta(days=days)
        try:
            rows = (
                Click.objects.filter(short_code=short_code, clicked_at__gte=since)
                .annotate(day=TruncDay("clicked_at"))
                .values("day")
                .annotate(count=Count("id"))
            )
            return [
                (row["day"].strftime("%Y-%m-%d") if row["day"] else "", row["count"])
                for row in rows
            ]
        except Exception as exc:
            logger.exception("click.time_series_failed short_code=%s", short_code)
            raise RepositoryError("get_click_time_series", short_code=short_code) from exc
