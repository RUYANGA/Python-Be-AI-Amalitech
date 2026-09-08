"""End-to-end smoke tests for the internal preview-fetch endpoint.

``build_preview_service`` is patched at the module it's imported into,
standing in for the real fetcher/breaker/cache wiring — the same style
``analytics``'s ``test_smoke.py`` uses for ``build_analytics_service``.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from apps.preview.api.interfaces.fetcher import PreviewResult

pytestmark = pytest.mark.django_db


class TestPreviewFetchView:
    def test_rejects_a_request_with_no_internal_token(self, api_client):
        response = api_client.post(
            "/api/v1/internal/preview/", {"url": "https://example.com/"}, format="json"
        )

        assert response.status_code == 403

    def test_returns_the_preview_for_a_valid_token(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        service = Mock()
        service.fetch.return_value = PreviewResult(
            title="Example Domain",
            description="An example.",
            favicon_url="https://example.com/favicon.ico",
        )

        with patch(
            "apps.preview.api.views.preview_view.build_preview_service",
            return_value=service,
        ):
            response = api_client.post(
                "/api/v1/internal/preview/",
                {"url": "https://example.com/"},
                format="json",
                HTTP_X_INTERNAL_TOKEN="shared-secret",
            )

        assert response.status_code == 200
        body = response.json()
        assert body == {
            "url": "https://example.com/",
            "title": "Example Domain",
            "description": "An example.",
            "favicon_url": "https://example.com/favicon.ico",
        }
        service.fetch.assert_called_once_with("https://example.com/")

    def test_rejects_a_request_with_the_wrong_token(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.post(
            "/api/v1/internal/preview/",
            {"url": "https://example.com/"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="wrong-token",
        )

        assert response.status_code == 403
