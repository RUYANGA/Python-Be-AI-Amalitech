"""Custom exceptions for the authentication service."""


class AuthError(Exception):
    """Base exception for all authentication errors."""


class UserAlreadyExistsError(AuthError):
    """Raised when attempting to register a user that already exists."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"User '{username}' already exists.")


class InvalidPasswordError(AuthError):
    """Raised when a password does not meet the security policy."""

    def __init__(
        self, message: str = "Password does not meet policy requirements."
    ) -> None:
        super().__init__(message)


class UserNotFoundError(AuthError):
    """Raised when a user cannot be found."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"User '{username}' not found.")


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid username or password.")
