"""Service contracts (abstract base classes) for the shortener API."""

from apps.shortener.api.interfaces.analytics import IClickAnalyticsRepository
from apps.shortener.api.interfaces.geo import IGeoLocator
from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLAggregateStats,
    URLListFilters,
)
from apps.shortener.api.interfaces.shortener import IShortCodeGenerator

__all__ = [
    "IClickAnalyticsRepository",
    "IGeoLocator",
    "IShortCodeGenerator",
    "IURLRepository",
    "KeysetPage",
    "URLAggregateStats",
    "URLListFilters",
]
