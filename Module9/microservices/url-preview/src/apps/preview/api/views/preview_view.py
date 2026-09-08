"""REST endpoint that fetches title/description/favicon for a destination URL.

Implements ``POST /api/v1/internal/preview/`` — called container-to-container
by the shortener service (fire-and-forget, from a Celery task) right after
a URL is shortened, so a slow or unreachable destination site can never make
the create endpoint itself slow. Authenticated with a shared static secret in
the ``X-Internal-Token`` header, never a user's JWT (this service has no
notion of one).
"""

from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.preview.api.exceptions import (
    CircuitOpenError,
    InvalidURLError,
    URLNotAccessibleError,
)
from apps.preview.api.permissions import HasInternalServiceToken
from apps.preview.api.serializers import PreviewRequestSerializer, PreviewResponseSerializer
from apps.preview.api.services.factory import build_preview_service

logger = logging.getLogger(__name__)


class PreviewFetchView(APIView):
    """Fetches preview metadata for a single URL, reported by the shortener service."""

    permission_classes = [HasInternalServiceToken]

    @extend_schema(exclude=True)
    def post(self, request: Request) -> Response:
        serializer = PreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data["url"]

        try:
            result = build_preview_service().fetch(url)
        except InvalidURLError as exc:
            logger.warning("preview_fetch.invalid_url url=%s error=%s", url, exc)
            return Response({"detail": str(exc)}, status=400)
        except CircuitOpenError as exc:
            logger.warning("preview_fetch.circuit_open url=%s domain=%s", url, exc.domain)
            return Response({"detail": f"Circuit open for domain '{exc.domain}'."}, status=503)
        except URLNotAccessibleError as exc:
            logger.warning("preview_fetch.not_accessible url=%s error=%s", url, exc)
            return Response({"detail": str(exc)}, status=503)

        response_serializer = PreviewResponseSerializer(
            {
                "url": url,
                "title": result.title,
                "description": result.description,
                "favicon_url": result.favicon_url,
            }
        )
        return Response(response_serializer.data, status=200)
