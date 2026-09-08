"""Unit tests for ``URLOwnershipClient`` — the REST call to shortener's
internal ownership-lookup endpoint.

Every network/HTTP failure path must fail *closed* — ``(False, None,
None)`` — since that's the guarantee that keeps a down shortener from
ever leaking someone else's analytics.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import requests

from apps.analytics.api.services.url_ownership_client import URLOwnershipClient


class TestGetOwnerId:
    def test_returns_the_owner_for_an_existing_code(self, settings):
        settings.SHORTENER_SERVICE_URL = "http://shortener.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"exists": True, "url_id": 5, "owner_id": 42}

        with patch(
            "apps.analytics.api.services.url_ownership_client.requests.get",
            return_value=mock_response,
        ) as get:
            result = URLOwnershipClient().get_owner_id("abc1234")

        get.assert_called_once_with(
            "http://shortener.test/api/v1/internal/urls/abc1234/owner/",
            headers={"X-Internal-Token": "shared-secret"},
            timeout=3.0,
        )
        assert result == (True, 5, 42)

    def test_returns_not_found_for_a_missing_code(self, settings):
        settings.SHORTENER_SERVICE_URL = "http://shortener.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"exists": False, "url_id": None, "owner_id": None}

        with patch(
            "apps.analytics.api.services.url_ownership_client.requests.get",
            return_value=mock_response,
        ):
            result = URLOwnershipClient().get_owner_id("doesnotexist")

        assert result == (False, None, None)

    def test_fails_closed_on_a_connection_error(self, settings):
        settings.SHORTENER_SERVICE_URL = "http://shortener.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        with patch(
            "apps.analytics.api.services.url_ownership_client.requests.get",
            side_effect=requests.ConnectionError("down"),
        ):
            result = URLOwnershipClient().get_owner_id("abc1234")

        assert result == (False, None, None)

    def test_fails_closed_on_an_http_error(self, settings):
        settings.SHORTENER_SERVICE_URL = "http://shortener.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        with patch(
            "apps.analytics.api.services.url_ownership_client.requests.get",
            return_value=mock_response,
        ):
            result = URLOwnershipClient().get_owner_id("abc1234")

        assert result == (False, None, None)

    def test_fails_closed_on_a_timeout(self, settings):
        settings.SHORTENER_SERVICE_URL = "http://shortener.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        with patch(
            "apps.analytics.api.services.url_ownership_client.requests.get",
            side_effect=requests.Timeout("timed out"),
        ):
            result = URLOwnershipClient().get_owner_id("abc1234")

        assert result == (False, None, None)
