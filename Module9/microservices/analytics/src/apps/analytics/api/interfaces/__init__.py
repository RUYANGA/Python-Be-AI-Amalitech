"""Service contracts (abstract base classes) for the analytics API."""

from apps.analytics.api.interfaces.analytics import (
    CountryStats,
    HourlyDistribution,
    IClickAnalyticsRepository,
    ReferrerStats,
    URLAggregateStats,
)

__all__ = [
    "CountryStats",
    "HourlyDistribution",
    "IClickAnalyticsRepository",
    "ReferrerStats",
    "URLAggregateStats",
]
