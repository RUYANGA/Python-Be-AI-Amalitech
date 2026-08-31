from abc import ABC, abstractmethod


class TokenService(ABC):
    """Contract for token lifecycle operations (Dependency Inversion)."""

    @abstractmethod
    def generate_tokens(self, user):
        """Return a dict with refresh and access tokens for the given user."""

    @abstractmethod
    def blacklist_refresh(self, refresh_token):
        """Invalidate a refresh token so it can no longer be used."""
