"""REST endpoint for the internal ownership lookup.

Implements ``GET /api/v1/internal/urls/<short_code>/owner/`` — the
service-to-service endpoint that replaced the old
``urlownership.ShortenerOwnership`` gRPC contract. The analytics service
has no ``urls`` table of its own, so "does this short code exist, and
who owns it?" has to be answered here.

Like the gRPC servicer it replaces, it is authenticated with a shared
static secret in the ``X-Internal-Token`` header, never a user's JWT.
"""

from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shortener.api.exceptions import URLNotFoundError
from apps.shortener.api.permissions import HasInternalServiceToken
from apps.shortener.api.services import build_url_service

logger = logging.getLogger(__name__)


class URLOwnershipView(APIView):
    """Answers existence/ownership questions about short codes."""

    permission_classes = [HasInternalServiceToken]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = build_url_service()

    @extend_schema(exclude=True)
    def get(self, _request: Request, short_code: str) -> Response:
        try:
            url = self.service.resolve(short_code)
        except URLNotFoundError:
            return Response({"exists": False, "url_id": None, "owner_id": None})

        return Response({"exists": True, "url_id": url.id, "owner_id": url.owner_id})
