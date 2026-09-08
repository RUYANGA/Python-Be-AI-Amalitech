"""Shared fixtures for the analytics service test suite."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.analytics.api.authentication import RemoteUser


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


@pytest.fixture(autouse=True)
def _celery_eager(settings):
    """Run Celery tasks synchronously, in-process, for the test suite.

    ``track_click_task.delay(...)`` would otherwise just enqueue onto
    Redis and return, so tests asserting on a ``Click`` row right after a
    request need the task to execute (and any exception to propagate)
    before ``.delay()`` returns — exactly what ``task_always_eager`` does.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
