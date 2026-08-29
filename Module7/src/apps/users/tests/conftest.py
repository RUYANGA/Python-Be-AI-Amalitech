"""Shared fixtures for the users test suite."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="alice",
        first_name="Alice",
        last_name="Doe",
        email="alice@example.com",
        password="testpass123",
    )


@pytest.fixture
def inactive_user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="bob",
        email="bob@example.com",
        password="testpass123",
        is_active=False,
    )


@pytest.fixture(autouse=True)
def _clear_login_rate_limit_keys():
    """Flush login-rate-limit Redis keys before and after each test.

    ``RedisLoginRateLimiter`` (the default rate limiter ``UserAuthService``
    builds when none is injected) writes to real Redis outside the DB
    transaction each test rolls back, so failed-attempt counters and blocks
    from one test would otherwise leak into the next.
    """
    from apps.shortener.api.cache.redis_client import get_redis_client

    client = get_redis_client()
    client.flush_pattern("auth:login_*")
    yield
    client.flush_pattern("auth:login_*")
