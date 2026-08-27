import logging

from django.contrib.auth import get_user_model

from apps.users.api.exceptions import AuthenticationError, InactiveAccountError
from apps.users.api.interfaces import AuthService, TokenService
from apps.users.api.services.token_service import JWTTokenService

User = get_user_model()

logger = logging.getLogger(__name__)


class UserAuthService(AuthService):
    """Orchestrates auth use-cases; each method has a single responsibility."""

    def __init__(self, token_service: TokenService | None = None):
        self.token_service = token_service or JWTTokenService()

    def register(self, data):
        password = data.pop("password")
        user = User(**data)
        user.set_password(password)
        user.save()
        logger.info("Registered new user: %s", user.username)
        return user

    def login(self, username, password):
        user = User.objects.filter(username=username).first()
        if user is None or not user.check_password(password):
            logger.warning("Failed login attempt for username: %s", username)
            raise AuthenticationError()
        if not user.is_active:
            logger.warning("Login attempt for inactive account: %s", username)
            raise InactiveAccountError()
        logger.info("User '%s' logged in successfully.", username)
        return {"user": user, "tokens": self.token_service.generate_tokens(user)}

    def logout(self, refresh_token):
        self.token_service.blacklist_refresh(refresh_token)
