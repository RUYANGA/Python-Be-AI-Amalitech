"""Tests for the nightly ``archive_expired_urls`` Celery Beat task."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.shortener.models import URL
from apps.shortener.tasks import archive_expired_urls_task

pytestmark = pytest.mark.django_db


class TestArchiveExpiredUrlsTask:
    def test_deactivates_expired_active_urls(self):
        expired = URL.objects.create(
            original_url="https://example.com/a",
            short_code="exp0001",
            expires_at=timezone.now() - timedelta(days=1),
            is_active=True,
        )

        archived = archive_expired_urls_task()

        assert archived == 1
        expired.refresh_from_db()
        assert expired.is_active is False

    def test_leaves_unexpired_urls_active(self):
        still_valid = URL.objects.create(
            original_url="https://example.com/b",
            short_code="exp0002",
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        archived = archive_expired_urls_task()

        assert archived == 0
        still_valid.refresh_from_db()
        assert still_valid.is_active is True

    def test_leaves_urls_without_an_expiry_active(self):
        no_expiry = URL.objects.create(
            original_url="https://example.com/c", short_code="exp0003", is_active=True
        )

        archived = archive_expired_urls_task()

        assert archived == 0
        no_expiry.refresh_from_db()
        assert no_expiry.is_active is True

    def test_skips_urls_already_archived(self):
        URL.objects.create(
            original_url="https://example.com/d",
            short_code="exp0004",
            expires_at=timezone.now() - timedelta(days=1),
            is_active=False,
        )

        archived = archive_expired_urls_task()

        assert archived == 0

    def test_invalidates_the_cache_for_each_archived_url(self):
        from apps.shortener.api.cache.redis_client import get_redis_client
        from apps.shortener.api.services.factory import build_url_service

        service = build_url_service()
        url = service._repository.create(original_url="https://example.com/e", short_code="exp0005")
        service.update(url, expires_at=timezone.now() - timedelta(days=1))
        # Repopulate the cache the way a normal read would, so there's
        # something for the archive task to actually invalidate.
        service.resolve("exp0005")
        cache = get_redis_client()
        assert cache.get("url:code:exp0005") is not None

        archive_expired_urls_task()

        assert cache.get("url:code:exp0005") is None
