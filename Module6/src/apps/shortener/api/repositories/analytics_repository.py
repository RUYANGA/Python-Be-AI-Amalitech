"""SQLAlchemy implementation of :class:`IClickAnalyticsRepository`.

Demonstrates SQLAlchemy patterns for analytics:
- ``func.count`` with ``group_by`` for aggregations
- ``func.date_trunc`` for time-bucketed analytics
- ``func.extract('hour', ...)`` for hourly distribution
- Atomic counter updates via ``update().values(click_count=...)``
- Session-scoped transactions
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, update

from apps.shortener.api.interfaces.analytics import (
    CountryStats,
    HourlyDistribution,
    IClickAnalyticsRepository,
    ReferrerStats,
)
from database.connection import get_session
from database.shortener.models import ClickModel, URLModel


class SQLAlchemyClickAnalyticsRepository(IClickAnalyticsRepository):
    def record_click(
        self,
        url: URLModel,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
        country: str = "",
    ) -> None:
        """Record a click and atomically increment the counter.

        Uses SQLAlchemy ``update()`` with a SQL expression to avoid
        race conditions — the UPDATE is a single
        ``SET click_count = click_count + 1`` at the database level.
        """
        session = get_session()
        try:
            click = ClickModel(
                url_id=url.id,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                country=country,
            )
            session.add(click)

            session.execute(
                update(URLModel)
                .where(URLModel.id == url.id)
                .values(
                    click_count=URLModel.click_count + 1,
                    last_accessed_at=datetime.now(UTC),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_country_breakdown(self, url: URLModel, limit: int = 10) -> list[CountryStats]:
        """Aggregate clicks by country using ``func.count`` + ``group_by``."""
        session = get_session()
        try:
            total = (
                session.query(func.count(ClickModel.id))
                .filter(ClickModel.url_id == url.id)
                .scalar()
            )
            if not total:
                return []

            rows = (
                session.query(ClickModel.country, func.count(ClickModel.id).label("clicks"))
                .filter(ClickModel.url_id == url.id, ClickModel.country != "")
                .group_by(ClickModel.country)
                .order_by(func.count(ClickModel.id).desc())
                .limit(limit)
                .all()
            )

            return [
                CountryStats(
                    country=row.country,
                    clicks=row.clicks,
                    percentage=round(row.clicks / total * 100, 1),
                )
                for row in rows
            ]
        finally:
            session.close()

    def get_referrer_breakdown(self, url: URLModel, limit: int = 10) -> list[ReferrerStats]:
        """Aggregate clicks by referer domain."""
        session = get_session()
        try:
            total = (
                session.query(func.count(ClickModel.id))
                .filter(ClickModel.url_id == url.id)
                .scalar()
            )
            if not total:
                return []

            rows = (
                session.query(ClickModel.referer, func.count(ClickModel.id).label("clicks"))
                .filter(ClickModel.url_id == url.id, ClickModel.referer != "")
                .group_by(ClickModel.referer)
                .order_by(func.count(ClickModel.id).desc())
                .limit(limit)
                .all()
            )

            return [
                ReferrerStats(
                    referer=row.referer,
                    clicks=row.clicks,
                    percentage=round(row.clicks / total * 100, 1),
                )
                for row in rows
            ]
        finally:
            session.close()

    def get_hourly_distribution(self, url: URLModel) -> list[HourlyDistribution]:
        """Bucket clicks by hour of day using ``func.extract('hour', ...)``.

        Returns a 24-slot list so the client can render a histogram.
        """
        since = datetime.now(UTC) - timedelta(days=30)
        session = get_session()
        try:
            hour_col = func.extract("hour", ClickModel.clicked_at).label("hour")
            rows = (
                session.query(hour_col, func.count(ClickModel.id).label("clicks"))
                .filter(ClickModel.url_id == url.id, ClickModel.clicked_at >= since)
                .group_by(hour_col)
                .order_by(hour_col)
                .all()
            )

            hourly_map = {int(row.hour): row.clicks for row in rows}
            return [HourlyDistribution(hour=h, clicks=hourly_map.get(h, 0)) for h in range(24)]
        finally:
            session.close()

    def get_recent_clicks(self, url: URLModel, limit: int = 20) -> list[dict]:
        """Return recent click records as lightweight dicts."""
        session = get_session()
        try:
            rows = (
                session.query(ClickModel)
                .filter(ClickModel.url_id == url.id)
                .order_by(ClickModel.clicked_at.desc())
                .limit(limit)
                .all()
            )
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
        finally:
            session.close()
