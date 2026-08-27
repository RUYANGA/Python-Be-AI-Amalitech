"""Owner-scoped URL operations keyed by ``short_code``.

Implements the Module 6 spec endpoints:

- ``GET /api/v1/urls/{short_code}/``   retrieve one of my URLs
- ``PUT /api/v1/urls/{short_code}/``   update one of my URLs
- ``DELETE /api/v1/urls/{short_code}/`` delete one of my URLs
"""

import logging

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import URLNotOwnedError
from apps.shortener.api.serializers import URLCreateSerializer, URLResponseSerializer
from apps.shortener.api.services.url_service import URLShortenerService
from apps.shortener.api.views.base_view import BaseURLView

logger = logging.getLogger(__name__)

SHORT_CODE_PARAMETER = OpenApiParameter(
    name="short_code",
    location=OpenApiParameter.PATH,
    type=str,
    description="The short code returned by POST /api/v1/urls/.",
)


class URLShortCodeDetailView(BaseURLView):
    """``GET/PUT/DELETE /api/v1/urls/{short_code}/`` — a URL you own, by code."""

    permission_classes = [IsAuthenticated]

    service: URLShortenerService

    @extend_schema(
        operation_id="urls_detail_by_code",
        parameters=[SHORT_CODE_PARAMETER],
        responses={
            200: URLResponseSerializer,
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Retrieve one of my URLs by short code",
        tags=["URLs"],
    )
    def get(self, request: Request, short_code: str) -> Response:
        try:
            url = self.service.get_owned_by_code(short_code, request.user)
        except URLNotOwnedError as exc:
            raise Http404(str(exc)) from exc
        serializer = URLResponseSerializer(url, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        operation_id="urls_update_by_code",
        parameters=[SHORT_CODE_PARAMETER],
        request=URLCreateSerializer,
        responses={
            200: URLResponseSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Update one of my URLs by short code",
        tags=["URLs"],
    )
    def put(self, request: Request, short_code: str) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            url = self.service.update_owned_by_code(
                short_code,
                request.user,
                original_url=serializer.validated_data["original_url"],
            )
        except URLNotOwnedError as exc:
            logger.warning(
                "urls.update_not_owned short_code=%s owner_id=%s",
                short_code,
                request.user.id,
            )
            raise Http404(str(exc)) from exc
        response = URLResponseSerializer(url, context={"request": request})
        return Response(response.data)

    @extend_schema(
        operation_id="urls_delete_by_code",
        parameters=[SHORT_CODE_PARAMETER],
        responses={
            200: OpenApiResponse(description="Deleted."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Delete one of my URLs by short code",
        tags=["URLs"],
    )
    def delete(self, request: Request, short_code: str) -> Response:
        try:
            self.service.delete_owned_by_code(short_code, request.user)
        except URLNotOwnedError as exc:
            logger.warning(
                "urls.delete_not_owned short_code=%s owner_id=%s",
                short_code,
                request.user.id,
            )
            raise Http404(str(exc)) from exc
        return Response(
            {"message": "URL deleted successfully."},
            status=status.HTTP_200_OK,
        )
