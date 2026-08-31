"""Shared fixtures for the shortener service test suite.

There's no local ``users`` table here, so "authenticating as a user" in
a test means handing DRF's test client a ``RemoteUser`` directly via
``force_authenticate`` — the same shape a real request would get from
``RemoteJWTAuthentication`` after verifying a JWT, just without needing
a real token or a running auth service.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.common.jwt_auth import RemoteUser


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user() -> RemoteUser:
    return RemoteUser(id=1, username="alice", is_premium=False, tier="free")


@pytest.fixture
def other_user() -> RemoteUser:
    return RemoteUser(id=2, username="bob", is_premium=False, tier="free")


@pytest.fixture(autouse=True)
def _clear_url_cache():
    """Flush cached URL entries before and after each test (see Module7 monolith)."""
    from apps.shortener.api.cache.redis_client import get_redis_client

    client = get_redis_client()
    client.flush_pattern("url:*")
    yield
    client.flush_pattern("url:*")
