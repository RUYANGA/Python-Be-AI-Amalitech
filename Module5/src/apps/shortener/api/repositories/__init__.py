"""Concrete repository implementations for the shortener API."""

from apps.shortener.api.repositories.url_repository import DjangoURLRepository

__all__ = ["DjangoURLRepository"]
