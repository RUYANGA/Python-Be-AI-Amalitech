"""Tests for the users API serializers."""

from __future__ import annotations

import pytest

from apps.users.api.serializers import (
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
)

pytestmark = pytest.mark.django_db


class TestLoginSerializer:
    def test_valid_payload(self):
        serializer = LoginSerializer(data={"username": "alice", "password": "secret"})
        assert serializer.is_valid()

    def test_requires_both_fields(self):
        serializer = LoginSerializer(data={})
        assert not serializer.is_valid()
        assert "username" in serializer.errors
        assert "password" in serializer.errors


class TestLogoutSerializer:
    def test_valid_payload(self):
        serializer = LogoutSerializer(data={"refresh": "sometoken"})
        assert serializer.is_valid()

    def test_requires_refresh(self):
        serializer = LogoutSerializer(data={})
        assert not serializer.is_valid()
        assert "refresh" in serializer.errors


class TestUserSerializer:
    def test_serializes_expected_fields(self, user):
        data = UserSerializer(user).data
        assert set(data.keys()) == {
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_premium",
            "tier",
        }
        assert data["username"] == "alice"


class TestRegisterSerializer:
    def test_valid_payload(self):
        serializer = RegisterSerializer(
            data={
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "new@example.com",
                "password": "StrongPass123",
            }
        )
        assert serializer.is_valid(), serializer.errors

    def test_rejects_short_password(self):
        serializer = RegisterSerializer(
            data={"username": "newuser", "email": "new@example.com", "password": "short"}
        )
        assert not serializer.is_valid()
        assert "password" in serializer.errors

    def test_rejects_duplicate_username(self, user):
        serializer = RegisterSerializer(
            data={
                "username": user.username,
                "email": "someoneelse@example.com",
                "password": "StrongPass123",
            }
        )
        assert not serializer.is_valid()
        assert "username" in serializer.errors
        assert "already exists" in str(serializer.errors["username"][0])

    def test_rejects_duplicate_email(self, user):
        serializer = RegisterSerializer(
            data={
                "username": "someoneelse",
                "email": user.email,
                "password": "StrongPass123",
            }
        )
        assert not serializer.is_valid()
        assert "email" in serializer.errors
