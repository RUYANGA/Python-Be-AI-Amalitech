"""Publishes click events for the analytics service to record.

This is the seam that replaces the old in-process ``record_click``: the
redirect/resolve endpoints are the highest-traffic, latency-critical,
unauthenticated path in the whole system, so they must never block on —
or fail because of — the analytics service being slow or down. The
``POST`` to analytics is dispatched on a background thread so
``publish()`` itself returns immediately; a delivery failure is logged
and swallowed, never raised.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# A handful of worker threads is plenty — each POST completes in
# milliseconds and this only ever needs to absorb short bursts, not
# sustain high throughput (that's what a message queue would be for).
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="click-publisher")


class ClickEventPublisher:
    """Publishes click events to the analytics service's internal REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 2.0,
    ) -> None:
        self._base_url = (base_url or settings.ANALYTICS_SERVICE_URL).rstrip("/")
        self._token = token or settings.INTERNAL_SERVICE_TOKEN
        self._timeout = timeout

    def publish(
        self,
        short_code: str,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
    ) -> None:
        payload = {
            "short_code": short_code,
            "ip_address": ip_address or "",
            "user_agent": user_agent,
            "referer": referer,
        }
        # Fire-and-forget: the caller (redirect/resolve view) must not
        # wait on analytics' response, so the actual request runs on a
        # background thread.
        _EXECUTOR.submit(self._send, payload)

    def _send(self, payload: dict) -> None:
        try:
            response = requests.post(
                f"{self._base_url}/api/v1/internal/clicks/",
                json=payload,
                headers={"X-Internal-Token": self._token},
                timeout=self._timeout,
            )
            response.raise_for_status()
            logger.debug("click_event.delivered short_code=%s", payload.get("short_code"))
        except requests.RequestException as exc:
            logger.warning(
                "click_event.publish_dropped short_code=%s error=%s",
                payload.get("short_code"),
                exc,
            )
