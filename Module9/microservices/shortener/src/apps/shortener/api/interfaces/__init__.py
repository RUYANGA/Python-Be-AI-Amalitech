"""Service contracts (abstract base classes) for the shortener API."""

from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLListFilters,
)
from apps.shortener.api.interfaces.shortener import IShortCodeGenerator

__all__ = ["IShortCodeGenerator", "IURLRepository", "KeysetPage", "URLListFilters"]
