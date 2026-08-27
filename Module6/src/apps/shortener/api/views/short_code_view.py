"""Owner-scoped URL operations keyed by ``short_code``.

Implements the Module 6 spec endpoints:

- ``GET /api/v1/urls/{short_code}/``   retrieve one of my URLs
- ``PATCH /api/v1/urls/{short_code}/``  partially update one of my URLs
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
from apps.shortener.api.serializers import URLResponseSerializer, URLUpdateSerializer
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
    """``GET/PATCH/DELETE /api/v1/urls/{short_code}/`` — a URL you own, by code."""

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
        operation_id="urls_partial_update_by_code",
        parameters=[SHORT_CODE_PARAMETER],
        request=URLUpdateSerializer,
        responses={
            200: URLResponseSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Partially update one of my URLs by short code",
        tags=["URLs"],
    )
    def patch(self, request: Request, short_code: str) -> Response:
        serializer = URLUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        try:
            url = self.service.partial_update_by_code(
                short_code,
                request.user,
                original_url=validated.get("original_url"),
                title=validated.get("title"),
                tags=validated.get("tags"),
                expires_at=validated.get("expires_at"),
            )
        except URLNotOwnedError as exc:
            logger.warning(
                "urls.patch_not_owned short_code=%s owner_id=%s",
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
