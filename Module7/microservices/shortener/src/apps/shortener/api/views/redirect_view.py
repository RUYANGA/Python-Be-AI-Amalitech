import logging

from django.http import Http404, HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from apps.shortener.api.exceptions import URLNotFoundError
from apps.shortener.api.services import ClickEventPublisher
from apps.shortener.api.views.base_view import BaseURLView

logger = logging.getLogger(__name__)


class URLRedirectView(BaseURLView):
    """``GET /<short_code>/`` — send a browser straight to the original URL.

    This is the link people actually click: the highest-traffic,
    unauthenticated, latency-critical endpoint in the whole system. The
    click event is *published*, not written in-process — the analytics
    service consumes it independently, so a slow or down analytics
    service can never make this redirect slow or fail.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._click_publisher = ClickEventPublisher()

    @extend_schema(exclude=True)
    def get(self, request: Request, short_code: str) -> HttpResponseRedirect:
        try:
            url = self.service.resolve(short_code)
        except URLNotFoundError as exc:
            logger.info("urls.redirect_missing short_code=%s", short_code)
            raise Http404(str(exc)) from exc

        self._click_publisher.publish(
            short_code,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referer=request.META.get("HTTP_REFERER", ""),
        )
        logger.info("urls.redirected short_code=%s url_id=%s", short_code, url.id)
        return HttpResponseRedirect(url.original_url)
