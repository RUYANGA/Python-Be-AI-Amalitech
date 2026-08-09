from abc import ABC, abstractmethod

from rest_framework_simplejwt.tokens import RefreshToken


class TokenService(ABC):
    """Abstraction over token lifecycle operations (Dependency Inversion)."""

    @abstractmethod
    def generate_tokens(self, user):
        """Return a dict with refresh and access tokens for the given user."""

    @abstractmethod
    def blacklist_refresh(self, refresh_token):
        """Invalidate a refresh token so it can no longer be used."""


class JWTTokenService(TokenService):
    """Concrete JWT implementation built on djangorestframework-simplejwt."""

    def generate_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def blacklist_refresh(self, refresh_token):
        RefreshToken(refresh_token).blacklist()
