"""Base domain exception for the shortener app.

Kept separate from Django/DRF's exception hierarchy so the service layer
stays framework-agnostic. Views translate these into HTTP responses.
"""

from __future__ import annotations


class ShortenerError(Exception):
    """Base class for shortener domain errors."""
