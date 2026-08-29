"""Tests for the users API service layer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.users.api.exceptions import AuthenticationError, InactiveAccountError
from apps.users.api.services import JWTTokenService, UserAuthService

pytestmark = pytest.mark.django_db


class TestUserAuthServiceRegister:
    def test_creates_and_returns_user(self):
        service = UserAuthService()
        user = service.register(
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "StrongPass123",
            }
        )
        assert user.pk is not None
        assert user.check_password("StrongPass123")


class TestUserAuthServiceLogin:
    def setup_method(self) -> None:
        self.token_service = MagicMock()
        self.token_service.generate_tokens.return_value = {
            "refresh": "refresh-token",
            "access": "access-token",
        }
        self.service = UserAuthService(token_service=self.token_service)

    def test_returns_user_and_tokens_on_success(self, user):
        result = self.service.login("alice", "testpass123")
        assert result["user"] == user
        assert result["tokens"] == {"refresh": "refresh-token", "access": "access-token"}
        self.token_service.generate_tokens.assert_called_once_with(user)

    def test_raises_for_unknown_username(self):
        with pytest.raises(AuthenticationError):
            self.service.login("nobody", "whatever")

    def test_raises_for_wrong_password(self, user):
        with pytest.raises(AuthenticationError):
            self.service.login("alice", "wrongpassword")

    def test_raises_for_inactive_account(self, inactive_user):
        with pytest.raises(InactiveAccountError):
            self.service.login("bob", "testpass123")


class TestUserAuthServiceLogout:
    def test_delegates_to_token_service(self):
        token_service = MagicMock()
        service = UserAuthService(token_service=token_service)

        service.logout("some-refresh-token")

        token_service.blacklist_refresh.assert_called_once_with("some-refresh-token")

    def test_defaults_to_jwt_token_service(self):
        service = UserAuthService()
        assert isinstance(service.token_service, JWTTokenService)


class TestJWTTokenService:
    def setup_method(self) -> None:
        self.service = JWTTokenService()

    def test_generate_tokens_returns_refresh_and_access(self, user):
        tokens = self.service.generate_tokens(user)
        assert set(tokens.keys()) == {"refresh", "access"}
        assert tokens["refresh"]
        assert tokens["access"]

    def test_blacklist_refresh_invalidates_token(self, user):
        tokens = self.service.generate_tokens(user)

        self.service.blacklist_refresh(tokens["refresh"])

        assert BlacklistedToken.objects.count() == 1
