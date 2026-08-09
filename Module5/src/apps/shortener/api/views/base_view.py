from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.shortener.api.services import build_url_service


class BaseURLView(APIView):
    """Shared base injecting the URL service into request views (DIP)."""

    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = build_url_service()
