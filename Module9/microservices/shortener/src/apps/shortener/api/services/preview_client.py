"""Calls the url-preview service's internal REST API.

Fetching a destination page's title/description/favicon can be slow or fail
outright (a dead domain, a slow server) — the url-preview service already
absorbs that with its own retry-with-backoff and per-domain circuit breaker
(see ``url-preview/README.md``). This client only needs to handle the much
shorter hop between the two containers: it's called from
``apps.shortener.tasks.fetch_url_preview_task``, itself dispatched
fire-and-forget from the create endpoint, so a failure here just means the
preview fields stay blank — never raised back to a caller.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreviewResult:
    title: str
    description: str
    favicon_url: str


class PreviewClient:
    """Fetches preview metadata for a URL via the url-preview service's internal REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = (base_url or settings.URL_PREVIEW_SERVICE_URL).rstrip("/")
        self._token = token or settings.INTERNAL_SERVICE_TOKEN
        self._timeout = timeout

    def fetch(self, url: str) -> PreviewResult | None:
        """Return preview metadata for ``url``, or ``None`` if it isn't available.

        Two different kinds of failure are treated differently:

        - A **connection failure or timeout** (url-preview unreachable —
          still starting up, briefly down) means we never got an answer at
          all, so it's re-raised for the caller (a Celery task with
          ``autoretry_for``) to retry with backoff.
        - Any other :class:`requests.RequestException` (a non-2xx response —
          url-preview *did* answer, e.g. its own circuit breaker is open for
          that domain, or the destination site is unreachable after
          url-preview's own retries) is a definitive answer, not a transient
          one: logged and swallowed, returning ``None`` rather than raising.
        """
        try:
            response = requests.post(
                f"{self._base_url}/api/v1/internal/preview/",
                json={"url": url},
                headers={"X-Internal-Token": self._token},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except (requests.ConnectionError, requests.Timeout):
            raise
        except requests.RequestException as exc:
            logger.warning("url_preview.request_failed url=%s error=%s", url, exc)
            return None

        data = response.json()
        return PreviewResult(
            title=data.get("title", ""),
            description=data.get("description", ""),
            favicon_url=data.get("favicon_url", ""),
        )
