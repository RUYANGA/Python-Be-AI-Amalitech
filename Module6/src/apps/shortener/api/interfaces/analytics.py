"""Abstraction for click analytics persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
    """Read operations for click analytics."""

    @abstractmethod
    def record_click(
        self,
        url,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
        country: str = "",
    ) -> None:
        """Record a single click event and increment the URL counter."""
        raise NotImplementedError

    @abstractmethod
    def get_country_breakdown(self, url, limit: int = 10) -> list[CountryStats]:
        """Return click counts grouped by country code."""
        raise NotImplementedError

    @abstractmethod
    def get_referrer_breakdown(self, url, limit: int = 10) -> list[ReferrerStats]:
        """Return click counts grouped by referer domain."""
        raise NotImplementedError

    @abstractmethod
    def get_hourly_distribution(self, url) -> list[HourlyDistribution]:
        """Return click distribution by hour of day (0-23)."""
        raise NotImplementedError

    @abstractmethod
    def get_recent_clicks(self, url, limit: int = 20) -> list[dict]:
        """Return the most recent click records for a URL."""
        raise NotImplementedError
