from __future__ import annotations

from apps.shortener.api.exceptions.base import ShortenerError


class ShortCodeGenerationError(ShortenerError):
    """Raised when a unique short code cannot be generated in time."""

    def __init__(
        self,
        message: str = "Failed to generate a unique short code after multiple attempts.",
    ) -> None:
        super().__init__(message)
