"""Base domain exception for the preview app.

Kept separate from Django/DRF's exception hierarchy so the service layer
stays framework-agnostic. Views translate these into HTTP responses.
"""

from __future__ import annotations


class PreviewError(Exception):
    """Base class for preview domain errors."""
