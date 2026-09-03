from __future__ import annotations

from apps.shortener.api.exceptions.base import ShortenerError


class CustomAliasNotAllowedError(ShortenerError):
    """Raised when a free-tier (or anonymous) user requests a custom alias."""

    def __init__(self) -> None:
        super().__init__("Custom aliases are a premium feature. Upgrade to premium to use one.")
