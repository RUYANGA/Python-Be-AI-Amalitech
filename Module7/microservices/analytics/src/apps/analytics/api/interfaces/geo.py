"""Abstraction for resolving a client IP to a country code (Dependency Inversion)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IGeoLocator(ABC):
    """Resolves an IP address to an ISO 3166-1 alpha-2 country code."""

    @abstractmethod
    def country_code(self, ip_address: str | None) -> str:
        """Return the two-letter country code for ``ip_address``.

        Returns ``""`` if ``ip_address`` is missing, private/reserved, or
        the country can't be determined — never raises.
        """
        raise NotImplementedError
