"""Base domain exception for the analytics app.

Kept separate from Django/DRF's exception hierarchy so the service layer
stays framework-agnostic. Views translate these into HTTP responses.
"""

from __future__ import annotations


class AnalyticsError(Exception):
    """Base class for analytics domain errors."""
