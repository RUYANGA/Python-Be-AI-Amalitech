from __future__ import annotations

from apps.users.api.exceptions.base import AuthError


class AuthenticationError(AuthError):
    """Raised when credentials don't match any active user."""

    def __init__(self) -> None:
        super().__init__("Invalid username or password.")
        self.code = "invalid_credentials"
