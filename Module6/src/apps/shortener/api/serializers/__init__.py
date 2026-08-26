"""Serializers for the shortener API endpoints."""

from apps.shortener.api.serializers.analytics_serializer import (
    AnalyticsSummarySerializer,
    ClickRecordSerializer,
    CountryStatsSerializer,
    HourlyDistributionSerializer,
    ReferrerStatsSerializer,
    URLAggregateStatsSerializer,
)
from apps.shortener.api.serializers.url_create_serializer import URLCreateSerializer
from apps.shortener.api.serializers.url_list_filter_serializer import URLListFilterSerializer
from apps.shortener.api.serializers.url_response_serializer import URLResponseSerializer

__all__ = [
    "AnalyticsSummarySerializer",
    "ClickRecordSerializer",
    "CountryStatsSerializer",
    "HourlyDistributionSerializer",
    "ReferrerStatsSerializer",
    "URLAggregateStatsSerializer",
    "URLCreateSerializer",
    "URLListFilterSerializer",
    "URLResponseSerializer",
]
