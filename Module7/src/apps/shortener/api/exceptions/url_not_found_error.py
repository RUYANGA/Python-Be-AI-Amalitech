from __future__ import annotations

from apps.shortener.api.exceptions.base import ShortenerError


class URLNotFoundError(ShortenerError):
    """Raised when a lookup by short code returns no result."""

    def __init__(self, short_code: str) -> None:
        super().__init__(f"URL with short code '{short_code}' was not found.")
        self.short_code = short_code
