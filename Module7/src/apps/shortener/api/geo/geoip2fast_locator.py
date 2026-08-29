"""Offline IP-to-country resolution via the bundled ``geoip2fast`` database.

``geoip2fast`` ships its own compact database (no MaxMind account or
per-lookup network call needed), so resolution is local and fast. Loading
that database takes tens of milliseconds, so the reader is a
module-level singleton built once per process rather than per request.
"""

from __future__ import annotations

import logging

from geoip2fast import GeoIP2Fast

from apps.shortener.api.interfaces.geo import IGeoLocator

logger = logging.getLogger(__name__)

_READER: GeoIP2Fast | None = None


def _get_reader() -> GeoIP2Fast:
    global _READER
    if _READER is None:
        _READER = GeoIP2Fast()
    return _READER


class GeoIP2FastLocator(IGeoLocator):
    """Resolves a client IP to a country code using the local geoip2fast database."""

    def country_code(self, ip_address: str | None) -> str:
        if not ip_address:
            return ""
        try:
            result = _get_reader().lookup(ip_address)
        except Exception:
            logger.warning("geoip.lookup_failed ip=%s", ip_address, exc_info=True)
            return ""
        if result.is_private or not result.country_code or result.country_code == "--":
            return ""
        return result.country_code
