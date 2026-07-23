"""Bcrypt implementation of the PasswordHasher protocol."""

import bcrypt


class BcryptPasswordHasher:
    """Concrete hasher using bcrypt.

    Follows the Single Responsibility Principle: only handles password hashing.
    Implements the PasswordHasher protocol (Liskov Substitution Principle).
    """

    def __init__(self, rounds: int = 12) -> None:
        """Initialize the hasher.

        Args:
            rounds: The bcrypt work factor (cost). Default is 12.
        """
        self._rounds = rounds

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using bcrypt.

        Args:
            password: The plaintext password.

        Returns:
            The bcrypt hash as a UTF-8 string.
        """
        salt = bcrypt.gensalt(rounds=self._rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify(self, password: str, hashed_password: str) -> bool:
        """Verify a password against a bcrypt hash.

        Args:
            password: The plaintext password.
            hashed_password: The stored bcrypt hash.

        Returns:
            True if the password matches, False otherwise.
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False
