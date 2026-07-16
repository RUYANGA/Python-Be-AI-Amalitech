"""In-memory implementation of the UserRepository protocol."""

from app.models import User


class InMemoryRepository:
    """Stores users in a dictionary (for testing and development).

    Follows the Single Responsibility Principle: only handles user persistence.
    Implements the UserRepository protocol (Liskov Substitution Principle).
    """

    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def save(self, user: User) -> None:
        """Persist a user in memory.

        Args:
            user: The User instance to save.
        """
        self._users[user.username] = user

    def find(self, username: str) -> User | None:
        """Find a user by username.

        Args:
            username: The username to search for.

        Returns:
            The User if found, None otherwise.
        """
        return self._users.get(username)
