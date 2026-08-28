"""Shared create mixin for the URL collection endpoint (``/api/v1/urls/``)."""

from __future__ import annotations

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import ShortCodeGenerationError
from apps.shortener.api.serializers import URLCreateSerializer, URLResponseSerializer

logger = logging.getLogger(__name__)


class URLCreateMixin:
    """``POST /api/v1/urls/`` — create a shortened URL, owned by the caller."""

    @extend_schema(
        operation_id="urls_create",
        request=URLCreateSerializer,
        responses={
            201: URLResponseSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            500: OpenApiResponse(description="Could not generate a unique short code."),
        },
        summary="Create a short URL",
        tags=["URLs"],
    )
    def post(self, request: Request) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            url = self.service.shorten(
                original_url=validated["original_url"],
                owner=request.user,
            )
        except ShortCodeGenerationError:
            logger.exception("url.create_failed reason=short_code_exhausted")
            return Response(
                {"detail": "Could not allocate a short code. Please retry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        title = validated.get("title", "")
        tag_names = validated.get("tags", [])
        expires_at = validated.get("expires_at")

        if title or tag_names or expires_at:
            updated = self.service.update(
                url,
                title=title or None,
                tags=tag_names or None,
                expires_at=expires_at,
            )
            url = updated

        response = URLResponseSerializer(url, context={"request": request})
        return Response(response.data, status=status.HTTP_201_CREATED)
