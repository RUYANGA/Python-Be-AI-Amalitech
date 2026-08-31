import logging

from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.api.interfaces import TokenService

logger = logging.getLogger(__name__)


class JWTTokenService(TokenService):
    """Concrete JWT implementation built on djangorestframework-simplejwt.

    The token is signed RS256 (see ``SIMPLE_JWT`` in settings) so the
    shortener and analytics services can verify it with only the public
    key. It also carries ``username``, ``is_premium`` and ``tier`` as
    custom claims: those services have no ``users`` table of their own
    to look the user up in, so anything they need to know about the
    caller (identity, premium status) has to travel *in* the token
    rather than be fetched afterwards.
    """

    def generate_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        refresh["username"] = user.username
        refresh["is_premium"] = user.is_premium
        refresh["tier"] = user.tier
        logger.debug("Generated tokens for user: %s", user.username)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def blacklist_refresh(self, refresh_token):
        RefreshToken(refresh_token).blacklist()
        logger.debug("Refresh token blacklisted.")
