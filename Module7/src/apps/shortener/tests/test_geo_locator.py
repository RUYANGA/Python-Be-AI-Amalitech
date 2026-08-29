"""Unit tests for :class:`GeoIP2FastLocator`."""

from __future__ import annotations

from apps.shortener.api.geo import GeoIP2FastLocator


class TestGeoIP2FastLocator:
    def setup_method(self) -> None:
        self.locator = GeoIP2FastLocator()

    def test_resolves_a_known_public_ip(self):
        assert self.locator.country_code("8.8.8.8") == "US"

    def test_returns_empty_for_private_ip(self):
        assert self.locator.country_code("172.20.0.1") == ""

    def test_returns_empty_for_missing_ip(self):
        assert self.locator.country_code(None) == ""
        assert self.locator.country_code("") == ""

    def test_returns_empty_for_invalid_ip(self):
        assert self.locator.country_code("not-an-ip") == ""
