"""REST endpoint that ingests click events from the shortener service.

Implements ``POST /api/v1/internal/clicks/`` — the service-to-service
endpoint that replaced the Kafka ``clicks`` topic and its
``consume_clicks`` consumer. The shortener service calls this once per
redirect/resolve, on a background thread, so a slow or unreachable
analytics service can never make those hot-path endpoints slow or fail.

Country/city are resolved here, not by the shortener service — geo
enrichment is an analytics concern. Like the ownership lookup this
service makes on the shortener, it is authenticated with a shared
static secret in the ``X-Internal-Token`` header, never a user's JWT.
"""

from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.api.exceptions import RepositoryError
from apps.analytics.api.geo import GeoIP2FastLocator
from apps.analytics.api.permissions import HasInternalServiceToken
from apps.analytics.api.services.factory import build_click_repository

logger = logging.getLogger(__name__)


class ClickIngestView(APIView):
    """Records a single click event reported by the shortener service."""

    permission_classes = [HasInternalServiceToken]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._repository = build_click_repository()
        self._geo_locator = GeoIP2FastLocator()

    @extend_schema(exclude=True)
    def post(self, request: Request) -> Response:
        short_code = request.data.get("short_code", "")
        if not short_code:
            logger.warning("click_ingest.dropped_malformed_entry data=%s", request.data)
            return Response({"detail": "short_code is required."}, status=400)

        ip_address = request.data.get("ip_address") or None
        country = self._geo_locator.country_code(ip_address)
        try:
            self._repository.record_click(
                short_code,
                ip_address=ip_address,
                user_agent=request.data.get("user_agent", ""),
                referer=request.data.get("referer", ""),
                country=country,
            )
        except RepositoryError:
            return Response({"detail": "Failed to record click."}, status=500)

        return Response(status=204)
