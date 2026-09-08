"""Shared fixtures for the url-preview service test suite.

There's no local ``users`` table and no JWT here — this service's only
route is gated by a shared internal token, not per-request identity — so
unlike ``shortener``'s conftest there's no ``RemoteUser``/``force_authenticate``
fixture to provide, just a plain ``APIClient`` and a Redis-flush fixture.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_preview_cache():
    """Flush cached preview/circuit-breaker keys before and after each test."""
    from apps.preview.api.cache.redis_client import get_redis_client

    client = get_redis_client()
    client.flush_pattern("preview:*")
    yield
    client.flush_pattern("preview:*")
