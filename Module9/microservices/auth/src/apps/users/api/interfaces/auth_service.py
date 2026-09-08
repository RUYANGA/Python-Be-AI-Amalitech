from abc import ABC, abstractmethod


class AuthService(ABC):
    """Contract for authentication use-cases (Interface Segregation)."""

    @abstractmethod
    def register(self, data):
        """Create a user from validated registration data."""

    @abstractmethod
    def login(self, username, password):
        """Authenticate credentials and return user plus tokens."""

    @abstractmethod
    def logout(self, refresh_token):
        """Invalidate the given refresh token."""
