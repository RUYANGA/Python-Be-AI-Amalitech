"""Analytics endpoints keyed by ``short_code``.

Implements the Module 6 spec endpoint:

- ``GET /api/v1/analytics/{short_code}/`` — time-series + geo analytics
"""

import logging

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import URLNotOwnedError
from apps.shortener.api.serializers import (
    AnalyticsSummarySerializer,
)
from apps.shortener.api.views.base_view import BaseURLView

logger = logging.getLogger(__name__)

SHORT_CODE_PARAMETER = OpenApiParameter(
    name="short_code",
    location=OpenApiParameter.PATH,
    type=str,
    description="The short code returned by POST /api/v1/urls/.",
)


class URLAnalyticsByCodeView(BaseURLView):
    """``GET /api/v1/analytics/{short_code}/`` — geo + time-series analytics."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="analytics_by_code",
        parameters=[SHORT_CODE_PARAMETER],
        responses={
            200: AnalyticsSummarySerializer,
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Get time-series and geo analytics for a URL by short code",
        tags=["Analytics"],
    )
    def get(self, request: Request, short_code: str) -> Response:
        try:
            url = self.service.get_owned_by_code(short_code, request.user)
        except URLNotOwnedError as exc:
            raise Http404(str(exc)) from exc

        stats = self.service.get_aggregate_stats(url)
        analytics_repo = self.service._analytics
        countries = analytics_repo.get_country_breakdown(url)
        referrers = analytics_repo.get_referrer_breakdown(url)
        hourly = analytics_repo.get_hourly_distribution(url)
        recent = analytics_repo.get_recent_clicks(url)
        days = int(request.query_params.get("days", 30))
        time_series = self.service.get_click_time_series(url, days=days)

        data = {
            "url_id": url.id,
            "short_code": url.short_code,
            "stats": stats,
            "countries": countries,
            "referrers": referrers,
            "hourly_distribution": hourly,
            "recent_clicks": recent,
            "time_series": [{"date": d, "clicks": c} for d, c in time_series],
        }
        serializer = AnalyticsSummarySerializer(
            {k: v for k, v in data.items() if k != "time_series"}
        )
        logger.info(
            "analytics.by_code short_code=%s owner_id=%s total_clicks=%s",
            short_code,
            request.user.id,
            getattr(stats, "total_clicks", None),
        )
        payload = serializer.data
        payload["time_series"] = data["time_series"]
        return Response(payload)
