"""Tests for the internal ownership-lookup endpoint.

Covers the REST contract that replaced the ``ShortenerOwnership`` gRPC
service: authenticated with ``X-Internal-Token``, never a user's JWT.
"""

from __future__ import annotations

import pytest

from apps.shortener.models import URL

pytestmark = pytest.mark.django_db


class TestURLOwnershipView:
    def test_rejects_a_request_without_the_internal_token(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.get("/api/v1/internal/urls/whatever/owner/")

        assert response.status_code == 401

    def test_rejects_a_request_with_the_wrong_internal_token(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.get(
            "/api/v1/internal/urls/whatever/owner/", HTTP_X_INTERNAL_TOKEN="wrong"
        )

        assert response.status_code == 401

    def test_returns_existence_and_owner_for_a_known_code(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        url = URL.objects.create(
            original_url="https://example.com", short_code="own9999", owner_id=42
        )

        response = api_client.get(
            f"/api/v1/internal/urls/{url.short_code}/owner/",
            HTTP_X_INTERNAL_TOKEN="shared-secret",
        )

        assert response.status_code == 200
        assert response.json() == {"exists": True, "url_id": url.id, "owner_id": 42}

    def test_returns_not_exists_for_an_unknown_code(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.get(
            "/api/v1/internal/urls/doesnotexist/owner/",
            HTTP_X_INTERNAL_TOKEN="shared-secret",
        )

        assert response.status_code == 200
        assert response.json() == {"exists": False, "url_id": None, "owner_id": None}
