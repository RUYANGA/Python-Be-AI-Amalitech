import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import ShortCodeGenerationError
from apps.shortener.api.serializers import URLCreateSerializer, URLResponseSerializer
from apps.shortener.api.views.base_view import BaseURLView

logger = logging.getLogger(__name__)


class URLCreateView(BaseURLView):
    """``POST /api/urls/`` — create a shortened URL.

    Anonymous creation is allowed in Module 5. Module 7 will require
    authentication and enforce per-tier limits.
    """

    @extend_schema(
        operation_id="urls_create",
        request=URLCreateSerializer,
        responses={
            201: URLResponseSerializer,
            400: OpenApiResponse(description="Invalid input."),
            500: OpenApiResponse(description="Could not generate a unique short code."),
        },
        summary="Create a short URL",
        tags=["URLs"],
    )
    def post(self, request: Request) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        owner = request.user if request.user.is_authenticated else None

        try:
            url = self.service.shorten(
                original_url=serializer.validated_data["original_url"],
                owner=owner,
            )
        except ShortCodeGenerationError:
            logger.exception("url.create_failed reason=short_code_exhausted")
            return Response(
                {"detail": "Could not allocate a short code. Please retry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = URLResponseSerializer(url, context={"request": request})
        return Response(response.data, status=status.HTTP_201_CREATED)
