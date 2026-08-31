"""Serializers for the analytics API endpoints."""

from apps.analytics.api.serializers.analytics_serializer import (
    AnalyticsSummarySerializer,
    ClickRecordSerializer,
    CountryStatsSerializer,
    HourlyDistributionSerializer,
    ReferrerStatsSerializer,
    TimeSeriesPointSerializer,
    URLAggregateStatsSerializer,
)

__all__ = [
    "AnalyticsSummarySerializer",
    "ClickRecordSerializer",
    "CountryStatsSerializer",
    "HourlyDistributionSerializer",
    "ReferrerStatsSerializer",
    "TimeSeriesPointSerializer",
    "URLAggregateStatsSerializer",
]
