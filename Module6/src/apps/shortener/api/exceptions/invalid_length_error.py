from __future__ import annotations

from apps.shortener.api.exceptions.base import ShortenerError


class InvalidShortCodeLengthError(ShortenerError):
    """Raised when a requested short code length is not a positive integer."""

    def __init__(self, length: int) -> None:
        super().__init__(f"Short code length must be a positive integer, got '{length}'.")
        self.length = length
