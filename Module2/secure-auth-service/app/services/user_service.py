"""User service containing core business logic.

Follows SOLID principles:
- SRP: Only handles authentication business logic
- OCP: New hashers/repos can be added without changing this class
- LSP: Any PasswordHasher/UserRepository implementation works
- ISP: Depends only on focused interfaces
- DIP: Depends on abstractions (PasswordHasher, UserRepository), not concretions
"""

import re

from app.exceptions import (
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.interfaces.password_hasher import PasswordHasher
from app.interfaces.user_repository import UserRepository
from app.logger import get_logger
from app.models import User

logger = get_logger()

_MIN_LENGTH = 8
_UPPERCASE = re.compile(r"[A-Z]")
_LOWERCASE = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")
_SYMBOL = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]")


class UserService:
    """Handles user registration and authentication.

    Dependencies (repository, hasher) are injected via the constructor,
    enabling easy testing and swappable implementations.
    """

    def __init__(
        self,
        repository: UserRepository,
        hasher: PasswordHasher,
    ) -> None:
        self._repository = repository
        self._hasher = hasher

    @property
    def hasher(self) -> PasswordHasher:
        """Expose the hasher for test inspection."""
        return self._hasher

    @property
    def repository(self) -> UserRepository:
        """Expose the repository for test inspection."""
        return self._repository

    def register(self, username: str, password: str) -> None:
        """Register a new user.

        Args:
            username: The desired username.
            password: The plaintext password.

        Raises:
            InvalidPasswordError: If password doesn't meet policy.
            UserAlreadyExistsError: If username is taken.
        """
        self._validate_password(password)

        if self._repository.find(username) is not None:
            logger.warning("Registration attempt for existing user: %s", username)
            raise UserAlreadyExistsError(username)

        password_hash = self._hasher.hash(password)
        user = User(username=username, password_hash=password_hash)
        self._repository.save(user)
        logger.info("User registered successfully: %s", username)

    def login(self, username: str, password: str) -> User:
        """Authenticate a user.

        Args:
            username: The username.
            password: The plaintext password.

        Returns:
            The authenticated User object.

        Raises:
            UserNotFoundError: If the user doesn't exist.
            InvalidCredentialsError: If the password is wrong.
        """
        user = self._repository.find(username)
        if user is None:
            logger.warning("Login attempt for non-existent user: %s", username)
            raise UserNotFoundError(username)

        if not self._hasher.verify(password, user.password_hash):
            logger.warning("Failed login attempt for user: %s", username)
            raise InvalidCredentialsError()

        logger.info("User logged in successfully: %s", username)
        return user

    def _validate_password(self, password: str) -> None:
        """Validate password against the security policy.

        Args:
            password: The plaintext password to validate.

        Raises:
            InvalidPasswordError: If the password fails any policy check.
        """
        errors: list[str] = []

        if len(password) < _MIN_LENGTH:
            errors.append(f"at least {_MIN_LENGTH} characters")
        if not _UPPERCASE.search(password):
            errors.append("an uppercase letter")
        if not _LOWERCASE.search(password):
            errors.append("a lowercase letter")
        if not _DIGIT.search(password):
            errors.append("a digit")
        if not _SYMBOL.search(password):
            errors.append("a special character")

        if errors:
            message = "Password must contain: " + ", ".join(errors)
            logger.warning("Password validation failed: %s", message)
            raise InvalidPasswordError(message)
