"""Tests for the internal token-validation endpoint.

Covers the REST contract that replaced the ``AuthTokenValidation`` gRPC
service: authenticated with ``X-Internal-Token``, returns the identity
claims embedded in a valid access token.
"""

from __future__ import annotations

import pytest
from rest_framework_simplejwt.tokens import AccessToken

pytestmark = pytest.mark.django_db


class TestTokenValidationView:
    def test_rejects_a_request_without_the_internal_token(self, api_client, user, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        token = str(AccessToken.for_user(user))

        response = api_client.post(
            "/api/v1/auth/internal/token/validate/", {"token": token}, format="json"
        )

        assert response.status_code == 401

    def test_rejects_a_request_with_the_wrong_internal_token(self, api_client, user, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        token = str(AccessToken.for_user(user))

        response = api_client.post(
            "/api/v1/auth/internal/token/validate/",
            {"token": token},
            format="json",
            HTTP_X_INTERNAL_TOKEN="wrong",
        )

        assert response.status_code == 401

    def test_returns_the_claims_for_a_valid_token(self, api_client, user, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        access = AccessToken.for_user(user)
        access["username"] = user.username
        access["is_premium"] = True
        access["tier"] = "pro"

        response = api_client.post(
            "/api/v1/auth/internal/token/validate/",
            {"token": str(access)},
            format="json",
            HTTP_X_INTERNAL_TOKEN="shared-secret",
        )

        assert response.status_code == 200
        assert response.json() == {
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "is_premium": True,
            "tier": "pro",
        }

    def test_returns_invalid_for_a_garbage_token(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.post(
            "/api/v1/auth/internal/token/validate/",
            {"token": "garbage"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="shared-secret",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is False
        assert "error" in body

    def test_returns_invalid_for_an_expired_token(self, api_client, user, settings):
        from datetime import timedelta

        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        access = AccessToken.for_user(user)
        access.set_exp(lifetime=timedelta(seconds=-1))

        response = api_client.post(
            "/api/v1/auth/internal/token/validate/",
            {"token": str(access)},
            format="json",
            HTTP_X_INTERNAL_TOKEN="shared-secret",
        )

        assert response.status_code == 200
        assert response.json()["valid"] is False
