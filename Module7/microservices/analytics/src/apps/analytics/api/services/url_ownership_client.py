"""The one cross-service call in this service — over REST.

Analytics has no ``urls`` table, so "does this short code exist, and is
it owned by the caller?" has to be answered by the shortener service,
which does own that data. This is deliberately the only place this
service makes a synchronous network call to another one — click
ingestion instead flows one-way through ``POST /api/v1/internal/clicks/``
so neither service can stall the other on its hot path.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class URLOwnershipClient:
    """Looks up a short code's owner via the shortener service's internal REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 3.0,
    ) -> None:
        self._base_url = (base_url or settings.SHORTENER_SERVICE_URL).rstrip("/")
        self._token = token or settings.INTERNAL_SERVICE_TOKEN
        self._timeout = timeout

    def get_owner_id(self, short_code: str) -> tuple[bool, int | None, int | None]:
        """Return ``(exists, url_id, owner_id)`` for ``short_code``.

        On a network failure this fails *closed* — ``(False, None, None)``
        — so a down shortener service can never leak someone else's
        analytics; it just makes analytics temporarily unavailable too.
        """
        try:
            response = requests.get(
                f"{self._base_url}/api/v1/internal/urls/{short_code}/owner/",
                headers={"X-Internal-Token": self._token},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("exists"):
                return False, None, None
            return True, data.get("url_id"), data.get("owner_id")
        except requests.RequestException as exc:
            logger.warning(
                "url_ownership.request_failed short_code=%s error=%s",
                short_code,
                exc,
            )
            return False, None, None
