"""Unit tests for ``RemoteJWTAuthentication``.

Mocks ``AuthServiceClient`` itself (rather than the underlying
``requests`` call) since what's under test here is the authentication
class's own logic — header parsing, building a ``RemoteUser`` from the
response, and translating a network/validation failure into
``AuthenticationFailed`` — not the REST client (see
``test_auth_service_client.py`` for that).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from apps.common.auth_service_client import TokenValidationResult
from apps.common.jwt_auth import RemoteJWTAuthentication


def _request(header: str | None = None):
    factory = APIRequestFactory()
    extra = {"HTTP_AUTHORIZATION": header} if header else {}
    return factory.get("/", **extra)


class TestRemoteJWTAuthentication:
    def test_returns_none_without_an_authorization_header(self):
        assert RemoteJWTAuthentication().authenticate(_request()) is None

    def test_returns_none_for_a_non_bearer_scheme(self):
        assert RemoteJWTAuthentication().authenticate(_request("Basic abc123")) is None

    def test_builds_a_remote_user_from_a_valid_token(self):
        result = TokenValidationResult(
            valid=True, user_id=9, username="bob", is_premium=True, tier="pro"
        )

        with patch("apps.common.jwt_auth.AuthServiceClient") as mock_client_cls:
            mock_client_cls.return_value.validate.return_value = result
            user, token = RemoteJWTAuthentication().authenticate(_request("Bearer sometoken"))

        assert user.id == 9
        assert user.username == "bob"
        assert user.is_premium_tier is True
        assert token == "sometoken"

    def test_rejects_a_token_the_auth_service_marks_invalid(self):
        result = TokenValidationResult(valid=False, error="Token is invalid")

        with patch("apps.common.jwt_auth.AuthServiceClient") as mock_client_cls:
            mock_client_cls.return_value.validate.return_value = result
            with pytest.raises(exceptions.AuthenticationFailed, match="Token is invalid"):
                RemoteJWTAuthentication().authenticate(_request("Bearer sometoken"))

    def test_treats_a_request_failure_as_authentication_failure(self):
        with patch("apps.common.jwt_auth.AuthServiceClient") as mock_client_cls:
            mock_client_cls.return_value.validate.side_effect = requests.ConnectionError("down")
            with pytest.raises(exceptions.AuthenticationFailed):
                RemoteJWTAuthentication().authenticate(_request("Bearer sometoken"))
