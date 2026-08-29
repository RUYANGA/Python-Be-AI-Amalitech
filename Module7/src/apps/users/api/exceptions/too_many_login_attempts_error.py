from __future__ import annotations

from apps.users.api.exceptions.base import AuthError


class TooManyLoginAttemptsError(AuthError):
    """Raised when a user is temporarily blocked after too many failed logins."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        minutes = max(1, retry_after_seconds // 60)
        unit = "minute" if minutes == 1 else "minutes"
        super().__init__(f"Too many failed login attempts. Please try again in {minutes} {unit}.")
        self.code = "too_many_attempts"
