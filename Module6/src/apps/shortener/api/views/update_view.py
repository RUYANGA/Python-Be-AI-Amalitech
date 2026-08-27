import logging

from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import URLNotOwnedError
from apps.shortener.api.serializers import URLCreateSerializer, URLResponseSerializer
from apps.shortener.api.services.url_service import URLShortenerService
from apps.shortener.api.views.params import ID_PARAMETER

logger = logging.getLogger(__name__)


class URLUpdateMixin:
    """``PATCH /api/urls/<id>/`` — update a URL you own."""

    service: URLShortenerService

    @extend_schema(
        operation_id="urls_update",
        parameters=[ID_PARAMETER],
        request=URLCreateSerializer,
        responses={
            200: URLResponseSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Update one of my URLs",
        tags=["URLs"],
    )
    def patch(self, request: Request, pk: int) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            url = self.service.update_owned(
                pk=pk,
                owner=request.user,
                original_url=serializer.validated_data["original_url"],
            )
        except URLNotOwnedError as exc:
            logger.warning("urls.update_not_owned id=%s owner_id=%s", pk, request.user.id)
            raise Http404(str(exc)) from exc

        logger.info("urls.updated id=%s owner_id=%s", pk, request.user.id)
        response = URLResponseSerializer(url, context={"request": request})
        return Response(response.data)
