import logging

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import URLNotFoundError
from apps.shortener.api.serializers import URLCreateSerializer
from apps.shortener.api.services import ClickEventPublisher
from apps.shortener.api.views.base_view import BaseURLView

logger = logging.getLogger(__name__)


class URLResolveView(BaseURLView):
    """``GET /<short_code>/`` — look up the original URL for a short code.

    Returns the URL as data (``200``) rather than issuing an HTTP redirect,
    so it's directly inspectable from any client — including Swagger UI's
    "Try it out", which otherwise can't show the result of a redirect to a
    cross-origin target.

    Also publishes a click event for the analytics service, the same way
    :class:`~apps.shortener.api.views.redirect_view.URLRedirectView` does.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._click_publisher = ClickEventPublisher()

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
    def get(self, request: Request, short_code: str) -> Response:
        try:
            url = self.service.resolve(short_code)
        except URLNotFoundError as exc:
            logger.info("urls.resolve_missing short_code=%s", short_code)
            raise Http404(str(exc)) from exc

        self._click_publisher.publish(
            short_code,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referer=request.META.get("HTTP_REFERER", ""),
        )
        logger.info("urls.resolved short_code=%s url_id=%s", short_code, url.id)
        return Response({"original_url": url.original_url})
