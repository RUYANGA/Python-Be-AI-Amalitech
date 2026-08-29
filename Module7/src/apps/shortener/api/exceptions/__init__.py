"""Domain exceptions for the shortener API."""

from apps.shortener.api.exceptions.base import ShortenerError
from apps.shortener.api.exceptions.invalid_length_error import (
    InvalidShortCodeLengthError,
)
from apps.shortener.api.exceptions.repository_error import RepositoryError
from apps.shortener.api.exceptions.short_code_generation_error import (
    ShortCodeGenerationError,
)
from apps.shortener.api.exceptions.url_not_found_error import URLNotFoundError
from apps.shortener.api.exceptions.url_not_owned_error import URLNotOwnedError

__all__ = [
    "InvalidShortCodeLengthError",
    "RepositoryError",
    "ShortCodeGenerationError",
    "ShortenerError",
    "URLNotFoundError",
    "URLNotOwnedError",
]
