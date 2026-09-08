import logging

from django.contrib.auth import get_user_model

from apps.users.api.exceptions import AuthenticationError, InactiveAccountError
from apps.users.api.interfaces import AuthService, LoginRateLimiter, TokenService
from apps.users.api.services.login_rate_limiter import RedisLoginRateLimiter
from apps.users.api.services.token_service import JWTTokenService

User = get_user_model()

logger = logging.getLogger(__name__)


class UserAuthService(AuthService):
    """Orchestrates auth use-cases; each method has a single responsibility."""

    def __init__(
        self,
        token_service: TokenService | None = None,
        rate_limiter: LoginRateLimiter | None = None,
    ):
        self.token_service = token_service or JWTTokenService()
        self.rate_limiter = rate_limiter or RedisLoginRateLimiter()

    def register(self, data):
        password = data.pop("password")
        user = User(**data)
        user.set_password(password)
        user.save()
        logger.info("Registered new user: %s", user.username)
        return user

    def login(self, username, password):
        self.rate_limiter.check(username)
        user = User.objects.filter(username=username).first()
        if user is None or not user.check_password(password):
            logger.warning("Failed login attempt for username: %s", username)
            remaining_attempts = self.rate_limiter.register_failure(username)
            raise AuthenticationError(remaining_attempts=remaining_attempts)
        if not user.is_active:
            logger.warning("Login attempt for inactive account: %s", username)
            raise InactiveAccountError()
        self.rate_limiter.reset(username)
        logger.info("User '%s' logged in successfully.", username)
        return {"user": user, "tokens": self.token_service.generate_tokens(user)}

    def logout(self, refresh_token):
        self.token_service.blacklist_refresh(refresh_token)
