"""Shared fixtures for the auth service test suite."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):  # noqa: ARG001 -- `db` activates DB access; it's a marker, not a value.
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="testpass123",
    )


@pytest.fixture(autouse=True)
def _clear_login_rate_limit_keys():
    """Flush login-rate-limit Redis keys before and after each test."""
    from apps.users.api.cache.redis_client import get_redis_client

    client = get_redis_client()
    client.delete("auth:login_attempts:alice")
    client.delete("auth:login_blocked:alice")
    yield
    client.delete("auth:login_attempts:alice")
    client.delete("auth:login_blocked:alice")
