"""Composition root for the analytics service."""

from __future__ import annotations

from apps.analytics.api.repositories.analytics_repository import DjangoClickAnalyticsRepository
from apps.analytics.api.services.analytics_service import AnalyticsService
from apps.analytics.api.services.url_ownership_client import URLOwnershipClient


def build_analytics_service() -> AnalyticsService:
    return AnalyticsService(
        repository=DjangoClickAnalyticsRepository(),
        ownership_client=URLOwnershipClient(),
    )
