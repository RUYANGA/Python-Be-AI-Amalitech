from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.users.api.services import UserAuthService


class BaseAuthView(APIView):
    """Shared base injecting the auth service into request views (DIP)."""

    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_service = UserAuthService()
