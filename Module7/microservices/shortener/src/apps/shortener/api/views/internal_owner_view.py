"""Service-to-service endpoint: "who owns this short code?"

The analytics service has no ``urls`` table of its own — when it needs
to check "does this URL exist, and does the caller own it?" (for the
premium analytics-by-code endpoint), it asks here instead. This is
*not* a user-facing endpoint: it is authenticated with a shared static
secret between the two services, not a user's JWT, and is not exposed
through the public gateway routes.
"""

from __future__ import annotations

import logging

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shortener.api.exceptions import URLNotFoundError
from apps.shortener.api.services import build_url_service

logger = logging.getLogger(__name__)


class InternalURLOwnerView(APIView):
    """``GET /internal/v1/urls/{short_code}/`` — existence + ownership only."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request, short_code: str) -> Response:
        provided = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
        if not settings.INTERNAL_SERVICE_TOKEN or provided != settings.INTERNAL_SERVICE_TOKEN:
            logger.warning("internal.owner_lookup_rejected short_code=%s", short_code)
            return Response({"detail": "Not authorized."}, status=403)

        service = build_url_service()
        try:
            url = service.resolve(short_code)
        except URLNotFoundError:
            return Response({"exists": False, "url_id": None, "owner_id": None})

        return Response({"exists": True, "url_id": url.id, "owner_id": url.owner_id})
