from __future__ import annotations

from apps.users.api.exceptions.base import AuthError


class EmailTakenError(AuthError):
    """Raised when registration uses an email that already exists."""

    def __init__(self, email: str) -> None:
        super().__init__("A user with this email already exists.")
        self.email = email
        self.code = "email_taken"
