"""Concrete implementation of :class:`IShortCodeGenerator`.

Uses the ``secrets`` module (CSPRNG) over a base62 alphabet.
"""

from __future__ import annotations

import secrets
import string

from apps.shortener.api.interfaces.shortener import IShortCodeGenerator


class Base62ShortCodeGenerator(IShortCodeGenerator):
    """Generates URL-safe codes drawn from ``[A-Za-z0-9]``.

    At length 7 the keyspace is 62**7 ≈ 3.5e12, which is comfortable for
    the collision-retry strategy used by the service layer.
    """

    _ALPHABET: str = string.ascii_letters + string.digits

    def generate(self, length: int = 7) -> str:
        if length <= 0:
            raise ValueError("length must be a positive integer")
        return "".join(secrets.choice(self._ALPHABET) for _ in range(length))
