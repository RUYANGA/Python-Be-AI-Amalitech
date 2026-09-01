"""Unit tests for ``AuthServiceClient`` — the REST call to auth's
internal token-validation endpoint.

Mocks ``requests.post`` directly rather than hitting a real auth
service: what matters here is that the client builds the right request
and parses the response correctly, not that HTTP itself works.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from apps.common.auth_service_client import AuthServiceClient, TokenValidationResult


class TestAuthServiceClient:
    def test_validate_posts_to_the_internal_endpoint_with_the_shared_token(self, settings):
        settings.AUTH_SERVICE_URL = "http://auth.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "valid": True,
            "user_id": 7,
            "username": "alice",
            "is_premium": True,
            "tier": "pro",
        }

        with patch(
            "apps.common.auth_service_client.requests.post", return_value=mock_response
        ) as post:
            result = AuthServiceClient().validate("some-token")

        post.assert_called_once_with(
            "http://auth.test/api/v1/auth/internal/token/validate/",
            json={"token": "some-token"},
            headers={"X-Internal-Token": "shared-secret"},
            timeout=3.0,
        )
        assert result == TokenValidationResult(
            valid=True, user_id=7, username="alice", is_premium=True, tier="pro"
        )

    def test_validate_strips_a_trailing_slash_from_the_base_url(self, settings):
        settings.AUTH_SERVICE_URL = "http://auth.test/"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"valid": False}

        with patch(
            "apps.common.auth_service_client.requests.post", return_value=mock_response
        ) as post:
            AuthServiceClient().validate("some-token")

        assert post.call_args[0][0] == "http://auth.test/api/v1/auth/internal/token/validate/"

    def test_validate_raises_on_a_non_2xx_response(self, settings):
        settings.AUTH_SERVICE_URL = "http://auth.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        with (
            patch("apps.common.auth_service_client.requests.post", return_value=mock_response),
            pytest.raises(requests.HTTPError),
        ):
            AuthServiceClient().validate("some-token")

    def test_validate_defaults_missing_fields_for_an_invalid_token(self, settings):
        settings.AUTH_SERVICE_URL = "http://auth.test"
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"valid": False, "error": "Token is invalid"}

        with patch("apps.common.auth_service_client.requests.post", return_value=mock_response):
            result = AuthServiceClient().validate("garbage")

        assert result.valid is False
        assert result.error == "Token is invalid"
        assert result.user_id == 0
        assert result.tier == "free"

    def test_explicit_constructor_args_override_settings(self):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"valid": False}

        with patch(
            "apps.common.auth_service_client.requests.post", return_value=mock_response
        ) as post:
            AuthServiceClient(base_url="http://override.test", token="explicit-token").validate(
                "some-token"
            )

        post.assert_called_once_with(
            "http://override.test/api/v1/auth/internal/token/validate/",
            json={"token": "some-token"},
            headers={"X-Internal-Token": "explicit-token"},
            timeout=3.0,
        )
