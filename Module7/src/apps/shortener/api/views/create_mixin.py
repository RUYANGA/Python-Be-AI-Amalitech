"""Shared create mixin for the URL collection endpoint (``/api/v1/urls/``)."""

from __future__ import annotations

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import (
    CustomAliasNotAllowedError,
    CustomAliasTakenError,
    ShortCodeGenerationError,
    URLLimitExceededError,
)
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
            403: OpenApiResponse(
                description="Free-tier active URL limit reached, or a custom alias was "
                "requested by a non-premium account."
            ),
            409: OpenApiResponse(description="The requested custom alias is already taken."),
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
            url = self.service.create(
                original_url=validated["original_url"],
                owner=request.user,
                title=validated.get("title") or None,
                tags=validated.get("tags") or None,
                expires_at=validated.get("expires_at"),
                custom_alias=validated.get("custom_alias") or None,
            )
        except URLLimitExceededError as exc:
            logger.warning("url.create_blocked_limit owner_id=%s", request.user.id)
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except CustomAliasNotAllowedError as exc:
            logger.warning("url.create_blocked_alias owner_id=%s", request.user.id)
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except CustomAliasTakenError as exc:
            logger.warning("url.create_blocked_alias_taken alias=%s", exc.alias)
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ShortCodeGenerationError:
            logger.exception("url.create_failed reason=short_code_exhausted")
            return Response(
                {"detail": "Could not allocate a short code. Please retry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = URLResponseSerializer(url, context={"request": request})
        return Response(response.data, status=status.HTTP_201_CREATED)
