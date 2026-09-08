import logging

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.shortener.api.services import build_url_service

logger = logging.getLogger(__name__)


class BaseURLView(APIView):
    """Shared base injecting the URL service into request views (DIP)."""

    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = build_url_service()
        logger.debug("url_service.built service=%s", type(self.service).__name__)

    @staticmethod
    def _get_client_ip(request: Request) -> str | None:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
