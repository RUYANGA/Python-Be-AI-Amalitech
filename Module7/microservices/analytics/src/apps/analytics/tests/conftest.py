"""Shared fixtures for the analytics service test suite."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.common.jwt_auth import RemoteUser


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def premium_user() -> RemoteUser:
    return RemoteUser(id=1, username="alice", is_premium=True, tier="pro")


@pytest.fixture
def free_user() -> RemoteUser:
    return RemoteUser(id=2, username="bob", is_premium=False, tier="free")


@pytest.fixture(autouse=True)
def _clear_analytics_cache():
    """Flush cached analytics entries before and after each test (see shortener's own)."""
    from apps.analytics.api.cache.redis_client import get_redis_client

    client = get_redis_client()
    client.flush_pattern("analytics:*")
    yield
    client.flush_pattern("analytics:*")
