from __future__ import annotations

from apps.shortener.api.exceptions.base import ShortenerError


class CustomAliasTakenError(ShortenerError):
    """Raised when the requested custom alias is already in use."""

    def __init__(self, alias: str) -> None:
        super().__init__(f"The alias '{alias}' is already taken.")
        self.alias = alias
