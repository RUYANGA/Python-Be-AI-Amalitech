from django.http import Http404, HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request

from apps.shortener.api.exceptions import URLNotFoundError
from apps.shortener.api.views.base_view import BaseURLView


class URLRedirectView(BaseURLView):
    """``GET /<short_code>/`` — redirect to the original URL."""

    @extend_schema(
        operation_id="urls_redirect",
        parameters=[
            OpenApiParameter(
                name="short_code",
                location=OpenApiParameter.PATH,
                type=str,
                description="The short code returned by POST /api/urls/.",
            )
        ],
        responses={
            302: OpenApiResponse(description="Redirect to the original URL."),
            404: OpenApiResponse(description="Short code not found."),
        },
        summary="Redirect to the original URL",
        description=(
            "Returns a 302 redirect to the original URL.\n\n"
            '**Note for Swagger UI:** clicking "Execute" here will usually show '
            '"Failed to fetch" / a CORS error. That\'s expected — Swagger UI runs '
            "requests through the browser's `fetch()`, which follows the 302 and "
            "then tries to load the target site as a cross-origin request; most "
            "sites don't grant CORS to arbitrary origins, so the browser blocks "
            "that second hop. The redirect itself still works. To verify it, open "
            "the URL directly in a new browser tab, or run "
            "`curl -v <base_url>/<short_code>/`."
        ),
        tags=["URLs"],
    )
    def get(self, _request: Request, short_code: str) -> HttpResponseRedirect:
        try:
            url = self.service.resolve(short_code)
        except URLNotFoundError as exc:
            raise Http404(str(exc)) from exc
        return HttpResponseRedirect(url.original_url)
