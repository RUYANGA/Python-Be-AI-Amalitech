import logging

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.users.api.services import UserAuthService

logger = logging.getLogger(__name__)


class BaseAuthView(APIView):
    """Shared base injecting the auth service into request views (DIP)."""

    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_service = UserAuthService()
        logger.debug("auth_service.built service=%s", type(self.auth_service).__name__)
