"""Composition root for the shortener service.

Keeps the concrete-implementation choices out of the view layer so
tests can substitute doubles without patching modules.
"""

from __future__ import annotations

from apps.shortener.api.repositories.url_repository import DjangoURLRepository
from apps.shortener.api.services.short_code_generator import Base62ShortCodeGenerator
from apps.shortener.api.services.url_service import URLShortenerService


def build_url_service() -> URLShortenerService:
    """Return a fully wired :class:`URLShortenerService`."""
    return URLShortenerService(
        repository=DjangoURLRepository(),
        generator=Base62ShortCodeGenerator(),
    )
