"""Serializers for the shortener API endpoints."""

from apps.shortener.api.serializers.analytics_serializer import (
    AnalyticsSummarySerializer,
    ClickRecordSerializer,
    CountryStatsSerializer,
    HourlyDistributionSerializer,
    ReferrerStatsSerializer,
    TimeSeriesPointSerializer,
    URLAggregateStatsSerializer,
)
from apps.shortener.api.serializers.url_create_serializer import URLCreateSerializer
from apps.shortener.api.serializers.url_list_filter_serializer import URLListFilterSerializer
from apps.shortener.api.serializers.url_response_serializer import URLResponseSerializer
from apps.shortener.api.serializers.url_update_serializer import URLUpdateSerializer

__all__ = [
    "AnalyticsSummarySerializer",
    "ClickRecordSerializer",
    "CountryStatsSerializer",
    "HourlyDistributionSerializer",
    "ReferrerStatsSerializer",
    "TimeSeriesPointSerializer",
    "URLAggregateStatsSerializer",
    "URLCreateSerializer",
    "URLListFilterSerializer",
    "URLResponseSerializer",
    "URLUpdateSerializer",
]
