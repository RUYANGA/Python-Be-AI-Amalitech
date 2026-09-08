"""Abstraction for click analytics persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class URLAggregateStats:
    """Aggregated statistics for a single short code."""

    total_clicks: int
    unique_countries: int
    top_referer: str
    last_clicked_at: datetime | None


@dataclass(frozen=True)
class CountryStats:
    country: str
    clicks: int
    percentage: float


@dataclass(frozen=True)
class ReferrerStats:
    referer: str
    clicks: int
    percentage: float


@dataclass(frozen=True)
class HourlyDistribution:
    hour: int
    clicks: int


class IClickAnalyticsRepository(ABC):
    """Read/write operations for click analytics, keyed by ``short_code``."""

    @abstractmethod
    def record_click(
        self,
        short_code: str,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
        country: str = "",
        city: str = "",
    ) -> None:
        """Record a single click event."""
        raise NotImplementedError

    @abstractmethod
    def get_aggregate_stats(self, short_code: str) -> URLAggregateStats:
        """Return aggregate click statistics for a short code."""
        raise NotImplementedError

    @abstractmethod
    def get_country_breakdown(self, short_code: str, limit: int = 10) -> list[CountryStats]:
        """Return click counts grouped by country code."""
        raise NotImplementedError

    @abstractmethod
    def get_referrer_breakdown(self, short_code: str, limit: int = 10) -> list[ReferrerStats]:
        """Return click counts grouped by referer domain."""
        raise NotImplementedError

    @abstractmethod
    def get_hourly_distribution(self, short_code: str) -> list[HourlyDistribution]:
        """Return click distribution by hour of day (0-23)."""
        raise NotImplementedError

    @abstractmethod
    def get_recent_clicks(self, short_code: str, limit: int = 20) -> list[dict]:
        """Return the most recent click records for a short code."""
        raise NotImplementedError

    @abstractmethod
    def get_click_time_series(self, short_code: str, days: int = 30) -> list[tuple[str, int]]:
        """Return daily click counts as ``(YYYY-MM-DD, count)`` tuples."""
        raise NotImplementedError
