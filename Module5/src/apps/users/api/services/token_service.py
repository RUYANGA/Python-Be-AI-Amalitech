import logging

from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.api.interfaces import TokenService

logger = logging.getLogger(__name__)


class JWTTokenService(TokenService):
    """Concrete JWT implementation built on djangorestframework-simplejwt."""

    def generate_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        logger.debug("Generated tokens for user: %s", user.username)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def blacklist_refresh(self, refresh_token):
        RefreshToken(refresh_token).blacklist()
        logger.debug("Refresh token blacklisted.")
