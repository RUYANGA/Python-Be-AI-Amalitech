"""Base domain exception for the users (auth) app.

Kept separate from Django/DRF's exception hierarchy so the service layer
stays framework-agnostic. Views translate these into HTTP responses.
"""

from __future__ import annotations


class AuthError(Exception):
    """Base class for auth domain errors."""
