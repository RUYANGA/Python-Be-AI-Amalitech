"""Integration tests for the users API views."""

from __future__ import annotations

import pytest
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


class TestRegisterView:
    def test_registers_a_new_user(self, api_client):
        response = api_client.post(
            "/api/auth/register/",
            {
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "new@example.com",
                "password": "StrongPass123",
            },
            format="json",
        )

        assert response.status_code == 201
        body = response.json()
        assert body["user"]["username"] == "newuser"

    def test_rejects_duplicate_username(self, api_client, user):
        response = api_client.post(
            "/api/auth/register/",
            {"username": user.username, "email": "other@example.com", "password": "StrongPass123"},
            format="json",
        )
        assert response.status_code == 400


class TestLoginView:
    def test_logs_in_with_valid_credentials(self, api_client, user):
        response = api_client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "testpass123"},
            format="json",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["username"] == "alice"
        assert "access" in body
        assert "refresh" in body

    def test_rejects_invalid_credentials(self, api_client, user):
        response = api_client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code == 400

    def test_rejects_inactive_account(self, api_client, inactive_user):
        response = api_client.post(
            "/api/auth/login/",
            {"username": "bob", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 400


class TestLogoutView:
    def test_logs_out_authenticated_user(self, api_client, user):
        api_client.force_authenticate(user=user)
        refresh = RefreshToken.for_user(user)

        response = api_client.post(
            "/api/auth/logout/",
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == 200

    def test_rejects_unauthenticated_request(self, api_client, user):
        refresh = RefreshToken.for_user(user)

        response = api_client.post(
            "/api/auth/logout/",
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == 401


class TestRefreshTokenView:
    def test_refreshes_access_token(self, api_client, user):
        refresh = RefreshToken.for_user(user)

        response = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.json()

    def test_rejects_invalid_refresh_token(self, api_client):
        response = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": "not-a-real-token"},
            format="json",
        )
        assert response.status_code == 401
