"""Concrete repository implementations for the shortener API.

All repositories use Django's built-in ORM as the primary data-access layer.
"""

from apps.shortener.api.repositories.analytics_repository import (
    DjangoClickAnalyticsRepository,
)
from apps.shortener.api.repositories.url_repository import DjangoURLRepository

__all__ = ["DjangoClickAnalyticsRepository", "DjangoURLRepository"]
