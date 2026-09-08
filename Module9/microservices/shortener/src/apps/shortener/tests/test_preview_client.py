"""Unit tests for ``PreviewClient``."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from apps.shortener.api.services.preview_client import PreviewClient, PreviewResult


class TestFetch:
    def test_posts_the_expected_payload_and_parses_the_response(self, settings):
        settings.URL_PREVIEW_SERVICE_URL = "http://url-preview.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "title": "Example",
            "description": "An example page.",
            "favicon_url": "https://example.com/favicon.ico",
        }

        with patch(
            "apps.shortener.api.services.preview_client.requests.post",
            return_value=mock_response,
        ) as post:
            result = PreviewClient().fetch("https://example.com/")

        post.assert_called_once_with(
            "http://url-preview.test/api/v1/internal/preview/",
            json={"url": "https://example.com/"},
            headers={"X-Internal-Token": "shared-secret"},
            timeout=10.0,
        )
        assert result == PreviewResult(
            title="Example",
            description="An example page.",
            favicon_url="https://example.com/favicon.ico",
        )

    def test_reraises_a_connection_failure_for_celery_to_retry(self, settings):
        settings.URL_PREVIEW_SERVICE_URL = "http://url-preview.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        with (
            patch(
                "apps.shortener.api.services.preview_client.requests.post",
                side_effect=requests.ConnectionError("down"),
            ),
            pytest.raises(requests.ConnectionError),
        ):
            PreviewClient().fetch("https://example.com/")

    def test_reraises_a_timeout_for_celery_to_retry(self, settings):
        settings.URL_PREVIEW_SERVICE_URL = "http://url-preview.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        with (
            patch(
                "apps.shortener.api.services.preview_client.requests.post",
                side_effect=requests.Timeout("slow"),
            ),
            pytest.raises(requests.Timeout),
        ):
            PreviewClient().fetch("https://example.com/")

    def test_swallows_a_definitive_non_2xx_response(self, settings):
        settings.URL_PREVIEW_SERVICE_URL = "http://url-preview.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")

        with patch(
            "apps.shortener.api.services.preview_client.requests.post",
            return_value=mock_response,
        ):
            result = PreviewClient().fetch("https://example.com/")

        assert result is None
