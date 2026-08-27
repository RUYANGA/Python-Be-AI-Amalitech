import logging

from rest_framework.permissions import AllowAny
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
