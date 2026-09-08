"""Tests for the nightly ``archive_expired_urls`` Celery Beat task."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.shortener.api.services.preview_client import PreviewResult
from apps.shortener.models import URL
from apps.shortener.tasks import archive_expired_urls_task, fetch_url_preview_task

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


class TestFetchUrlPreviewTask:
    def _patch_client(self, result):
        return patch(
            "apps.shortener.tasks.PreviewClient.fetch",
            return_value=result,
        )

    def test_backfills_description_and_favicon_and_a_blank_title(self):
        url = URL.objects.create(
            original_url="https://example.com/a", short_code="prv0001", title=""
        )
        result = PreviewResult(
            title="Example Domain",
            description="An example page.",
            favicon_url="https://example.com/favicon.ico",
        )

        with self._patch_client(result):
            updated = fetch_url_preview_task(url.id, url.original_url)

        assert updated is True
        url.refresh_from_db()
        assert url.title == "Example Domain"
        assert url.description == "An example page."
        assert url.favicon_url == "https://example.com/favicon.ico"

    def test_never_overwrites_a_user_supplied_title(self):
        url = URL.objects.create(
            original_url="https://example.com/b",
            short_code="prv0002",
            title="My own title",
        )
        result = PreviewResult(
            title="Fetched Title", description="Fetched description.", favicon_url=""
        )

        with self._patch_client(result):
            fetch_url_preview_task(url.id, url.original_url)

        url.refresh_from_db()
        assert url.title == "My own title"
        assert url.description == "Fetched description."

    def test_leaves_fields_blank_when_preview_is_unavailable(self):
        url = URL.objects.create(original_url="https://example.com/c", short_code="prv0003")

        with self._patch_client(None):
            updated = fetch_url_preview_task(url.id, url.original_url)

        assert updated is False
        url.refresh_from_db()
        assert url.description == ""
        assert url.favicon_url == ""

    def test_invalidates_the_cache_after_updating(self):
        from apps.shortener.api.cache.redis_client import get_redis_client
        from apps.shortener.api.services.factory import build_url_service

        service = build_url_service()
        url = service._repository.create(original_url="https://example.com/d", short_code="prv0004")
        service.resolve("prv0004")  # populate the cache the way a normal read would
        cache = get_redis_client()
        assert cache.get("url:code:prv0004") is not None

        result = PreviewResult(title="", description="Fetched.", favicon_url="")
        with self._patch_client(result):
            fetch_url_preview_task(url.id, url.original_url)

        assert cache.get("url:code:prv0004") is None
