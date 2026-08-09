from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import URLNotFoundError
from apps.shortener.api.serializers import URLCreateSerializer
from apps.shortener.api.views.base_view import BaseURLView


class URLResolveView(BaseURLView):
    """``GET /<short_code>/`` — look up the original URL for a short code.

    Returns the URL as data (``200``) rather than issuing an HTTP redirect,
    so it's directly inspectable from any client — including Swagger UI's
    "Try it out", which otherwise can't show the result of a redirect to a
    cross-origin target (the browser's fetch() follows the redirect and
    then gets blocked by CORS on the destination site).
    """

    @extend_schema(
        operation_id="urls_resolve",
        parameters=[
            OpenApiParameter(
                name="short_code",
                location=OpenApiParameter.PATH,
                type=str,
                description="The short code returned by POST /api/urls/.",
            )
        ],
        responses={
            200: URLCreateSerializer,
            404: OpenApiResponse(description="Short code not found."),
        },
        summary="Look up the original URL for a short code",
        tags=["URLs"],
    )
    def get(self, _request: Request, short_code: str) -> Response:
        try:
            url = self.service.resolve(short_code)
        except URLNotFoundError as exc:
            raise Http404(str(exc)) from exc
        return Response({"original_url": url.original_url})
