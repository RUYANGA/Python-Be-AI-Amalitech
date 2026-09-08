"""Offline IP-to-country resolution via the bundled ``geoip2fast`` database.

Geo enrichment moved here from the shortener service along with click
tracking — resolving a country code is an analytics concern, not a
routing one, and the redirect endpoint no longer needs it at all.
"""

from __future__ import annotations

import logging

from geoip2fast import GeoIP2Fast

from apps.analytics.api.interfaces.geo import IGeoLocator

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
