"""Analytics orchestration: ownership check + aggregate reporting.

Mirrors the shortener monolith's ``URLShortenerService.get_analytics_summary``,
but split across the service boundary: ownership lives in the shortener
service (``URLOwnershipClient``), the actual click data lives here.
"""

from __future__ import annotations

import logging

from apps.analytics.api.exceptions import URLNotAccessibleError
from apps.analytics.api.interfaces.analytics import IClickAnalyticsRepository
from apps.analytics.api.services.url_ownership_client import URLOwnershipClient

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(
        self,
        repository: IClickAnalyticsRepository,
        ownership_client: URLOwnershipClient,
    ) -> None:
        self._repository = repository
        self._ownership = ownership_client

    def get_summary_for_owner(self, short_code: str, requester_id: int, days: int = 30) -> dict:
        """Return the full analytics summary for ``short_code``.

        Raises :class:`URLNotAccessibleError` if the short code doesn't
        exist, or isn't owned by ``requester_id`` — the shortener
        service is the source of truth for both.
        """
        exists, url_id, owner_id = self._ownership.get_owner_id(short_code)
        if not exists or owner_id != requester_id:
            logger.warning(
                "analytics.not_accessible short_code=%s requester_id=%s", short_code, requester_id
            )
            raise URLNotAccessibleError(short_code)

        time_series = self._repository.get_click_time_series(short_code, days=days)
        return {
            "url_id": url_id,
            "short_code": short_code,
            "stats": self._repository.get_aggregate_stats(short_code),
            "countries": self._repository.get_country_breakdown(short_code),
            "referrers": self._repository.get_referrer_breakdown(short_code),
            "hourly_distribution": self._repository.get_hourly_distribution(short_code),
            "recent_clicks": self._repository.get_recent_clicks(short_code),
            "time_series": [{"date": date, "clicks": clicks} for date, clicks in time_series],
        }
