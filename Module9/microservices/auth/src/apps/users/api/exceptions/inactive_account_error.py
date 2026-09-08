from __future__ import annotations

from apps.users.api.exceptions.base import AuthError


class InactiveAccountError(AuthError):
    """Raised when a valid user account is not active."""

    def __init__(self) -> None:
        super().__init__("This account is inactive.")
        self.code = "inactive_account"
