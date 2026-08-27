from __future__ import annotations

import logging

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.serializers import (
    AnalyticsSummarySerializer,
)
from apps.shortener.api.views.base_view import BaseURLView

logger = logging.getLogger(__name__)


class URLAnalyticsView(BaseURLView):
    """``GET /api/urls/<id>/analytics/`` — full analytics dashboard for a URL."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="urls_analytics",
        parameters=[
            OpenApiParameter(name="id", location=OpenApiParameter.PATH, type=int),
        ],
        responses={
            200: AnalyticsSummarySerializer,
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Get analytics for a URL",
        tags=["Analytics"],
    )
    def get(self, request: Request, pk: int) -> Response:
        url = self._get_owned_or_404(pk, request.user)

        stats = self.service.get_aggregate_stats(url)
        analytics_repo = self.service._analytics
        countries = analytics_repo.get_country_breakdown(url)
        referrers = analytics_repo.get_referrer_breakdown(url)
        hourly = analytics_repo.get_hourly_distribution(url)
        recent = analytics_repo.get_recent_clicks(url)

        data = {
            "url_id": url.id,
            "short_code": url.short_code,
            "stats": stats,
            "countries": countries,
            "referrers": referrers,
            "hourly_distribution": hourly,
            "recent_clicks": recent,
        }
        serializer = AnalyticsSummarySerializer(data)
        logger.info(
            "urls.analytics url_id=%s owner_id=%s total_clicks=%s",
            url.id,
            request.user.id,
            getattr(stats, "total_clicks", None),
        )
        return Response(serializer.data)

    def _get_owned_or_404(self, pk: int, user):
        url = self.service._repository.get_by_id(pk)
        if url is None or url.owner_id != user.id:
            raise Http404("URL not found.")
        return url


class URLTimeSeriesView(BaseURLView):
    """``GET /api/urls/<id>/analytics/timeseries/`` — daily click counts."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="urls_time_series",
        parameters=[
            OpenApiParameter(name="id", location=OpenApiParameter.PATH, type=int),
            OpenApiParameter(
                name="days",
                location=OpenApiParameter.QUERY,
                type=int,
                default=30,
                description="Number of days to look back.",
            ),
        ],
        responses={
            200: dict,
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Get daily click time series",
        tags=["Analytics"],
    )
    def get(self, request: Request, pk: int) -> Response:
        url = self._get_owned_or_404(pk, request.user)
        days = int(request.query_params.get("days", 30))

        time_series = self.service.get_click_time_series(url, days=days)
        logger.info(
            "urls.time_series url_id=%s owner_id=%s days=%d points=%d",
            url.id,
            request.user.id,
            days,
            len(time_series),
        )
        return Response(
            {
                "url_id": url.id,
                "short_code": url.short_code,
                "days": days,
                "time_series": [{"date": d, "clicks": c} for d, c in time_series],
            }
        )

    def _get_owned_or_404(self, pk: int, user):
        url = self.service._repository.get_by_id(pk)
        if url is None or url.owner_id != user.id:
            raise Http404("URL not found.")
        return url


class TopURLsView(BaseURLView):
    """``GET /api/urls/top/`` — top URLs by click count for the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="urls_top",
        parameters=[
            OpenApiParameter(
                name="limit",
                location=OpenApiParameter.QUERY,
                type=int,
                default=10,
                description="Number of top URLs to return.",
            ),
        ],
        responses={200: dict},
        summary="Get top URLs by click count",
        tags=["Analytics"],
    )
    def get(self, request: Request) -> Response:
        limit = int(request.query_params.get("limit", 10))
        top_urls = self.service.get_top_urls(request.user, limit=limit)
        logger.info("urls.top owner_id=%s limit=%d count=%d", request.user.id, limit, len(top_urls))

        from apps.shortener.api.serializers import URLResponseSerializer

        data = [
            {
                "url": URLResponseSerializer(url, context={"request": request}).data,
                "total_clicks": clicks,
            }
            for url, clicks in top_urls
        ]
        return Response({"top_urls": data})
