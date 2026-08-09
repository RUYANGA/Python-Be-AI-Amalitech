from abc import ABC, abstractmethod

from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from apps.users.api.services.token_service import JWTTokenService, TokenService

User = get_user_model()


class AuthService(ABC):
    """Interface for authentication use-cases (Interface Segregation)."""

    @abstractmethod
    def register(self, data):
        """Create a user from validated registration data."""

    @abstractmethod
    def login(self, username, password):
        """Authenticate credentials and return user plus tokens."""

    @abstractmethod
    def logout(self, refresh_token):
        """Invalidate the given refresh token."""


class UserAuthService(AuthService):
    """Orchestrates auth use-cases; each method has a single responsibility."""

    def __init__(self, token_service: TokenService | None = None):
        self.token_service = token_service or JWTTokenService()

    def register(self, data):
        password = data.pop("password")
        user = User(**data)
        user.set_password(password)
        user.save()
        return user

    def login(self, username, password):
        user = User.objects.filter(username=username).first()
        if user is None or not user.check_password(password):
            raise ValidationError({"detail": "Invalid username or password."})
        if not user.is_active:
            raise ValidationError({"detail": "This account is inactive."})
        return {"user": user, "tokens": self.token_service.generate_tokens(user)}

    def logout(self, refresh_token):
        self.token_service.blacklist_refresh(refresh_token)
