"""Concrete repository implementations for the shortener API.

All repositories use Django's built-in ORM as the primary data-access layer.
"""

from apps.shortener.api.repositories.cached_url_repository import CachedURLRepository
from apps.shortener.api.repositories.url_repository import DjangoURLRepository

__all__ = ["CachedURLRepository", "DjangoURLRepository"]
