"""Integration tests for the URL create + redirect views."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.shortener.api.exceptions import ShortCodeGenerationError
from apps.shortener.models import URL

pytestmark = pytest.mark.django_db


class TestURLCreateView:
    def test_creates_short_url_anonymously(self, api_client):
        response = api_client.post(
            "/api/urls/",
            {"original_url": "https://example.com/some/path"},
            format="json",
        )

        assert response.status_code == 201
        body = response.json()
        assert body["original_url"] == "https://example.com/some/path"
        assert len(body["short_code"]) == 7
        assert body["short_url"].endswith(f"/{body['short_code']}/")

    def test_persists_url_owned_by_authenticated_user(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(
            "/api/urls/",
            {"original_url": "https://example.com/owned"},
            format="json",
        )

        assert response.status_code == 201
        url = URL.objects.get(short_code=response.json()["short_code"])
        assert url.owner == user

    def test_rejects_invalid_url(self, api_client):
        response = api_client.post(
            "/api/urls/",
            {"original_url": "not a url"},
            format="json",
        )
        assert response.status_code == 400

    def test_rejects_missing_field(self, api_client):
        response = api_client.post("/api/urls/", {}, format="json")
        assert response.status_code == 400
        assert "original_url" in response.json()

    def test_returns_500_when_short_code_generation_fails(self, api_client):
        with patch("apps.shortener.api.views.base_view.build_url_service") as mock_build:
            mock_build.return_value.shorten.side_effect = ShortCodeGenerationError()

            response = api_client.post(
                "/api/urls/",
                {"original_url": "https://example.com/fail"},
                format="json",
            )

        assert response.status_code == 500


class TestURLRedirectView:
    def test_redirects_to_original_url(self, api_client):
        create = api_client.post(
            "/api/urls/",
            {"original_url": "https://example.com/target"},
            format="json",
        )
        short_code = create.json()["short_code"]

        redirect = api_client.get(f"/{short_code}/")

        assert redirect.status_code == 302
        assert redirect["Location"] == "https://example.com/target"

    def test_returns_404_for_unknown_code(self, api_client):
        response = api_client.get("/nonexist/")
        assert response.status_code == 404
