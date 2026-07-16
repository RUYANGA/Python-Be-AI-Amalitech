"""Interface for user persistence (Dependency Inversion Principle)."""

from typing import Protocol, runtime_checkable

from app.models import User


@runtime_checkable
class UserRepository(Protocol):
    """Protocol defining the contract for user storage implementations.

    Any repository (InMemory, SQLite, Postgres, etc.) must implement these methods.
    """

    def save(self, user: User) -> None:
        """Persist a user.

        Args:
            user: The User instance to save.
        """
        ...

    def find(self, username: str) -> User | None:
        """Find a user by username.

        Args:
            username: The username to search for.

        Returns:
            The User if found, None otherwise.
        """
        ...
