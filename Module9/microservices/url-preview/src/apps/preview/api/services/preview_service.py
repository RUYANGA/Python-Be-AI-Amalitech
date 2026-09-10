"""URL preview business logic.

The orchestrator (mirrors ``URLShortenerService``'s role in the
shortener service): validates the URL, guards against SSRF, checks a
short result cache, consults the per-domain circuit breaker, then
retries the actual fetch with backoff. Depends only on the
``IPreviewFetcher`` interface and the Redis client — never imports
``requests``/``BeautifulSoup`` directly, so those stay swappable/mockable.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import socket
from urllib.parse import urlparse

from apps.preview.api.cache.redis_client import RedisClient
from apps.preview.api.exceptions import (
    CircuitOpenError,
    InvalidURLError,
    PreviewFetchError,
    URLNotAccessibleError,
)
from apps.preview.api.interfaces.fetcher import IPreviewFetcher, PreviewResult
from apps.preview.api.profiling import timed
from apps.preview.api.services.circuit_breaker import DomainCircuitBreaker
from apps.preview.api.services.retry import call_with_backoff

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = frozenset({"http", "https"})


class PreviewService:
    """Fetches, caches, and resiliently retries URL preview metadata."""

    def __init__(
        self,
        fetcher: IPreviewFetcher,
        breaker: DomainCircuitBreaker,
        cache: RedisClient,
        max_attempts: int,
        base_delay: float,
        cache_ttl: int,
    ) -> None:
        self._fetcher = fetcher
        self._breaker = breaker
        self._cache = cache
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._cache_ttl = cache_ttl

    @timed(enabled=True)
    def fetch(self, url: str) -> PreviewResult:
        """Return the :class:`PreviewResult` for ``url``.

        Raises ``InvalidURLError`` (bad scheme, or the SSRF guard
        rejects the resolved address), ``CircuitOpenError`` (the domain's
        circuit is currently open — no network call is made), or
        ``URLNotAccessibleError`` (every retry attempt failed).
        """
        domain = self._validate_and_resolve(url)

        cache_key = self._cache_key(url)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return PreviewResult(**cached)

        if not self._breaker.allow(domain):
            raise CircuitOpenError(domain)

        try:
            result = call_with_backoff(
                lambda: self._fetcher.fetch(url),
                max_attempts=self._max_attempts,
                base_delay=self._base_delay,
                retry_on=(PreviewFetchError,),
            )
        except PreviewFetchError as exc:
            self._breaker.record_failure(domain)
            raise URLNotAccessibleError(url) from exc

        self._breaker.record_success(domain)
        self._cache.set(
            cache_key,
            {
                "title": result.title,
                "description": result.description,
                "favicon_url": result.favicon_url,
            },
            ttl=self._cache_ttl,
        )
        return result

    # ------------------------------------------------------------------
    # Validation / SSRF guard
    # ------------------------------------------------------------------

    def _validate_and_resolve(self, url: str) -> str:
        """Validate ``url``'s scheme and hostname, returning the hostname.

        Rejects anything but ``http``/``https``, and — since this service
        fetches arbitrary attacker-influenceable URLs into the internal
        Docker network — resolves the hostname and rejects any resolved
        address that's private/loopback/link-local/reserved/multicast.
        """
        parsed = urlparse(url)
        if parsed.scheme not in _ALLOWED_SCHEMES:
            raise InvalidURLError(f"URL scheme must be http or https, got '{parsed.scheme}'.")

        hostname = parsed.hostname
        if not hostname:
            raise InvalidURLError(f"URL '{url}' has no hostname.")

        try:
            addr_infos = socket.getaddrinfo(hostname, None)
        except OSError as exc:
            logger.warning(
                "preview_service.dns_resolution_failed hostname=%s error=%s", hostname, exc
            )
            raise InvalidURLError(f"Could not resolve hostname '{hostname}'.") from exc

        for _family, _type, _proto, _canonname, sockaddr in addr_infos:
            raw_ip = sockaddr[0]
            ip = ipaddress.ip_address(raw_ip)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                logger.warning(
                    "preview_service.ssrf_guard_rejected hostname=%s ip=%s", hostname, raw_ip
                )
                raise InvalidURLError(f"URL '{url}' resolves to a disallowed address.")

        return hostname

    @staticmethod
    def _cache_key(url: str) -> str:
        return f"preview:cache:{hashlib.sha256(url.encode()).hexdigest()}"
