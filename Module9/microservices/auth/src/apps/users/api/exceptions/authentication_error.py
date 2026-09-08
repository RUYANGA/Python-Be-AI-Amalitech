from __future__ import annotations

from apps.users.api.exceptions.base import AuthError


class AuthenticationError(AuthError):
    """Raised when credentials don't match any active user."""

    def __init__(self, remaining_attempts: int | None = None) -> None:
        self.remaining_attempts = remaining_attempts
        message = "Invalid username or password."
        if remaining_attempts is not None:
            if remaining_attempts > 0:
                unit = "attempt" if remaining_attempts == 1 else "attempts"
                message = (
                    f"{message} {remaining_attempts} {unit} remaining "
                    "before your account is temporarily locked."
                )
            else:
                message = (
                    f"{message} No attempts remaining; your account has been temporarily locked."
                )
        super().__init__(message)
        self.code = "invalid_credentials"
