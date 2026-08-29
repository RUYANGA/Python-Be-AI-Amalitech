import logging

from django.http import Http404, HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from apps.shortener.api.exceptions import URLNotFoundError
from apps.shortener.api.views.base_view import BaseURLView

logger = logging.getLogger(__name__)


class URLRedirectView(BaseURLView):
    """``GET /<short_code>/`` — send a browser straight to the original URL.

    This is the link people actually click. Unlike ``URLResolveView``
    (the JSON-returning API endpoint under ``/api/v1/<short_code>/``),
    it issues a real HTTP redirect so pasting the short link into a
    browser lands on the original page.
    """

    @extend_schema(exclude=True)
    def get(self, request: Request, short_code: str) -> HttpResponseRedirect:
        try:
            url = self.service.resolve(short_code)
        except URLNotFoundError as exc:
            logger.info("urls.redirect_missing short_code=%s", short_code)
            raise Http404(str(exc)) from exc

        self.service.record_click(
            url,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referer=request.META.get("HTTP_REFERER", ""),
        )
        logger.info("urls.redirected short_code=%s url_id=%s", short_code, url.id)
        return HttpResponseRedirect(url.original_url)
