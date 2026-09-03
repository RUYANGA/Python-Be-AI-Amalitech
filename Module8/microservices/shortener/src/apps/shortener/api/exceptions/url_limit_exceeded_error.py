from __future__ import annotations

from apps.shortener.api.exceptions.base import ShortenerError


class URLLimitExceededError(ShortenerError):
    """Raised when a free-tier user has reached the max active URL limit."""

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Free accounts are limited to {limit} active URLs. "
            "Upgrade to premium for unlimited URLs."
        )
        self.limit = limit
