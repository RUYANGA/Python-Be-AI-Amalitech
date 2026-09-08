"""Analytics endpoint keyed by ``short_code``.

``GET /api/v1/analytics/{short_code}/`` — time-series + geo analytics,
premium accounts only (see ``IsPremiumUser``).
"""

from __future__ import annotations

import logging

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.api.exceptions import URLNotAccessibleError
from apps.analytics.api.permissions import IsPremiumUser
from apps.analytics.api.serializers import AnalyticsSummarySerializer
from apps.analytics.api.services import build_analytics_service

logger = logging.getLogger(__name__)

SHORT_CODE_PARAMETER = OpenApiParameter(
    name="short_code",
    location=OpenApiParameter.PATH,
    type=str,
    description="The short code returned by the shortener service's POST /api/v1/urls/.",
)


class URLAnalyticsByCodeView(APIView):
    """``GET /api/v1/analytics/{short_code}/`` — geo + time-series analytics.

    Premium-only. Ownership is verified against the shortener service
    (this service has no ``urls`` table of its own) before any click
    data is returned.
    """

    permission_classes = [IsPremiumUser]

    @extend_schema(
        operation_id="analytics_by_code",
        parameters=[SHORT_CODE_PARAMETER],
        responses={
            200: AnalyticsSummarySerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Premium account required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Get time-series and geo analytics for a URL by short code",
        tags=["Analytics"],
        description="Premium-only: the caller must be a premium user.",
    )
    def get(self, request: Request, short_code: str) -> Response:
        days = int(request.query_params.get("days", 30))
        service = build_analytics_service()
        try:
            summary = service.get_summary_for_owner(short_code, request.user.id, days=days)
        except URLNotAccessibleError as exc:
            raise Http404(str(exc)) from exc

        serializer = AnalyticsSummarySerializer(summary)
        logger.info(
            "analytics.by_code short_code=%s requester_id=%s total_clicks=%s",
            short_code,
            request.user.id,
            summary["stats"].total_clicks,
        )
        return Response(serializer.data)
