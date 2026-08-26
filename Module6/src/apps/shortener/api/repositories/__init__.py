"""Concrete repository implementations for the shortener API.

All repositories use SQLAlchemy as the primary data-access layer.
"""

from apps.shortener.api.repositories.analytics_repository import (
    SQLAlchemyClickAnalyticsRepository,
)
from apps.shortener.api.repositories.url_repository import SQLAlchemyURLRepository

__all__ = ["SQLAlchemyClickAnalyticsRepository", "SQLAlchemyURLRepository"]
