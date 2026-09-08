"""End-to-end smoke tests for the auth service's public HTTP contract.

Not a full parity re-test of the monolith's users-app suite (that logic
is unchanged and already covered there) — this exists to prove the
service boundary itself works: register, login, rate limiting, and the
one thing that's new here — the access token actually carries the
cross-service claims (``username``/``is_premium``/``tier``) that the
shortener and analytics services depend on.
"""

from __future__ import annotations

import jwt
import pytest

pytestmark = pytest.mark.django_db


class TestRegisterAndLogin:
    def test_register_then_login_returns_tokens(self, api_client):
        register = api_client.post(
            "/api/v1/auth/register/",
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "StrongPass123",
            },
            format="json",
        )
        assert register.status_code == 201

        login = api_client.post(
            "/api/v1/auth/login/",
            {"username": "newuser", "password": "StrongPass123"},
            format="json",
        )
        assert login.status_code == 200
        assert "access" in login.json()
        assert "refresh" in login.json()

    def test_access_token_carries_cross_service_claims(self, api_client, user):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": user.username, "password": "testpass123"},
            format="json",
        )
        access = response.json()["access"]

        # Signature already exercised by simplejwt's own config; decoding
        # unverified here only to inspect the claim payload for this assertion.
        claims = jwt.decode(access, options={"verify_signature": False})

        assert claims["username"] == user.username
        assert claims["is_premium"] is False
        assert claims["tier"] == "free"
        assert "user_id" in claims

    def test_rejects_invalid_credentials(self, api_client, user):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": user.username, "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code == 401


class TestLoginRateLimiting:
    def test_blocks_after_five_failed_attempts(self, api_client, user):
        for _ in range(5):
            response = api_client.post(
                "/api/v1/auth/login/",
                {"username": user.username, "password": "wrongpassword"},
                format="json",
            )
            assert response.status_code == 401

        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": "alice", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 429
