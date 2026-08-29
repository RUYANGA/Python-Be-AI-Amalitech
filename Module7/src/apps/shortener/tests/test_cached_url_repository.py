"""Unit tests for the Redis caching layer around ``list_with_filters``."""

from __future__ import annotations

import fnmatch
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from apps.shortener.api.interfaces.repository import KeysetPage, URLListFilters
from apps.shortener.api.repositories.cached_url_repository import CachedURLRepository
from apps.shortener.models import URL


class FakeRedisClient:
    """Minimal in-memory stand-in for :class:`RedisClient`."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ttl=None):
        self._store[key] = value
        return True

    def delete(self, key):
        return bool(self._store.pop(key, None))

    def flush_pattern(self, pattern):
        matched = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
        for k in matched:
            del self._store[k]
        return len(matched)


def _make_url(pk: int, owner_id: int, short_code: str) -> URL:
    now = datetime.now(UTC)
    return URL(
        id=pk,
        original_url="https://example.com",
        short_code=short_code,
        title="",
        owner_id=owner_id,
        click_count=0,
        is_active=True,
        expires_at=None,
        last_accessed_at=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def fake_redis() -> FakeRedisClient:
    return FakeRedisClient()


@pytest.fixture
def fake_orm(fake_redis) -> Mock:
    orm = Mock()
    orm.list_with_filters.return_value = KeysetPage(
        items=[_make_url(1, owner_id=7, short_code="abc1234")],
        next_cursor=None,
        has_more=False,
    )
    return orm


@pytest.fixture
def repo(fake_orm, fake_redis) -> CachedURLRepository:
    return CachedURLRepository(orm_repository=fake_orm, redis_client=fake_redis)


class TestListWithFiltersCaching:
    def test_second_identical_call_is_served_from_cache(self, repo, fake_orm):
        filters = URLListFilters(owner_id=7)

        first = repo.list_with_filters(filters, limit=20, cursor=None)
        second = repo.list_with_filters(filters, limit=20, cursor=None)

        assert fake_orm.list_with_filters.call_count == 1
        assert [u.short_code for u in first.items] == [u.short_code for u in second.items]

    def test_different_filters_are_not_conflated(self, repo, fake_orm):
        repo.list_with_filters(URLListFilters(owner_id=7), limit=20, cursor=None)
        repo.list_with_filters(URLListFilters(owner_id=7, search="foo"), limit=20, cursor=None)

        assert fake_orm.list_with_filters.call_count == 2

    def test_different_owners_are_not_conflated(self, repo, fake_orm):
        repo.list_with_filters(URLListFilters(owner_id=7), limit=20, cursor=None)
        repo.list_with_filters(URLListFilters(owner_id=8), limit=20, cursor=None)

        assert fake_orm.list_with_filters.call_count == 2

    def test_create_invalidates_the_owners_cached_lists(self, repo, fake_orm):
        filters = URLListFilters(owner_id=7)
        repo.list_with_filters(filters, limit=20, cursor=None)
        assert fake_orm.list_with_filters.call_count == 1

        fake_orm.create.return_value = _make_url(2, owner_id=7, short_code="new0001")
        repo.create(original_url="https://example.com/new", short_code="new0001", owner=None)

        repo.list_with_filters(filters, limit=20, cursor=None)
        assert fake_orm.list_with_filters.call_count == 2

    def test_delete_invalidates_the_owners_cached_lists(self, repo, fake_orm):
        filters = URLListFilters(owner_id=7)
        repo.list_with_filters(filters, limit=20, cursor=None)
        assert fake_orm.list_with_filters.call_count == 1

        repo.delete(_make_url(1, owner_id=7, short_code="abc1234"))

        repo.list_with_filters(filters, limit=20, cursor=None)
        assert fake_orm.list_with_filters.call_count == 2

    def test_write_for_other_owner_does_not_invalidate(self, repo, fake_orm):
        filters = URLListFilters(owner_id=7)
        repo.list_with_filters(filters, limit=20, cursor=None)
        assert fake_orm.list_with_filters.call_count == 1

        repo.delete(_make_url(9, owner_id=8, short_code="other001"))

        repo.list_with_filters(filters, limit=20, cursor=None)
        assert fake_orm.list_with_filters.call_count == 1
