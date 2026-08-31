from __future__ import annotations

from apps.users.api.exceptions.base import AuthError


class UsernameTakenError(AuthError):
    """Raised when registration uses a username that already exists."""

    def __init__(self, username: str) -> None:
        super().__init__("A user with this username already exists.")
        self.username = username
        self.code = "username_taken"
