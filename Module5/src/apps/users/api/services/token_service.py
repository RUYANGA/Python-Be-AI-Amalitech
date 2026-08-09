from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.api.interfaces import TokenService


class JWTTokenService(TokenService):
    """Concrete JWT implementation built on djangorestframework-simplejwt."""

    def generate_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def blacklist_refresh(self, refresh_token):
        RefreshToken(refresh_token).blacklist()
