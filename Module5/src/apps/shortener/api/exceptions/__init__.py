"""Domain exceptions for the shortener API."""

from apps.shortener.api.exceptions.base import ShortenerError
from apps.shortener.api.exceptions.short_code_generation_error import (
    ShortCodeGenerationError,
)
from apps.shortener.api.exceptions.url_not_found_error import URLNotFoundError

__all__ = ["ShortCodeGenerationError", "ShortenerError", "URLNotFoundError"]
