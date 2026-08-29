"""Abstraction for short-code generators (Dependency Inversion).

Any algorithm — base62 random, hashids, sequential, custom — is a valid
implementation as long as it fulfils this contract. Consumers (services,
views) depend on this interface, never on a concrete class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class IShortCodeGenerator(ABC):
    """Produces short codes for URL entries."""

    @abstractmethod
    def generate(self, length: int = 7) -> str:
        """Return a newly generated code of ``length`` characters.

        Implementations MUST NOT check the database for uniqueness — that
        is the service's responsibility (Single Responsibility Principle).
        """
        raise NotImplementedError
