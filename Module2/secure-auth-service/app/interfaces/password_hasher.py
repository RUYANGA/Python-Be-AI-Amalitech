"""Interface for password hashing (Dependency Inversion Principle)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PasswordHasher(Protocol):
    """Protocol defining the contract for password hashing implementations.

    Any hasher (Bcrypt, Argon2, etc.) must implement these methods.
    """

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password.

        Args:
            password: The plaintext password to hash.

        Returns:
            The hashed password string.
        """
        ...

    def verify(self, password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: The plaintext password to verify.
            hashed_password: The stored hash to compare against.

        Returns:
            True if the password matches, False otherwise.
        """
        ...
