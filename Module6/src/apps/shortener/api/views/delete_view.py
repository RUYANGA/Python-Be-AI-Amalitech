import logging

from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import URLNotOwnedError
from apps.shortener.api.services.url_service import URLShortenerService
from apps.shortener.api.views.params import ID_PARAMETER

logger = logging.getLogger(__name__)


class URLDeleteMixin:
    """``DELETE /api/urls/<id>/`` — delete a URL you own."""

    service: URLShortenerService

    @extend_schema(
        operation_id="urls_delete",
        parameters=[ID_PARAMETER],
        responses={
            200: OpenApiResponse(description="Deleted."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="URL not found."),
        },
        summary="Delete one of my URLs",
        tags=["URLs"],
    )
    def delete(self, request: Request, pk: int) -> Response:
        try:
            self.service.delete_owned(pk=pk, owner=request.user)
        except URLNotOwnedError as exc:
            logger.warning("urls.delete_not_owned id=%s owner_id=%s", pk, request.user.id)
            raise Http404(str(exc)) from exc
        logger.info("urls.deleted id=%s owner_id=%s", pk, request.user.id)
        return Response(
            {"message": "URL deleted successfully."},
            status=status.HTTP_200_OK,
        )
