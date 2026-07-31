"""Integration tests against a real local PostgreSQL instance.

Unit tests elsewhere mock every repository, so they can't verify the schema,
connection pooling, or — the main event — that the transactional follow
actually behaves atomically against a real database. These tests do that.
Skips cleanly if Postgres isn't reachable so the suite stays portable.
"""

import psycopg2
import pytest

from social_media.config.settings import settings
from social_media.database.postgres_connection import PostgresConnection
from social_media.repositories.postgres_repos import (
    FollowerRepository,
    PostRepository,
    UserRepository,
)

try:
    _pg = PostgresConnection(settings)
    _connect_error = None
except Exception as exc:  # pragma: no cover - environment dependent
    _pg = None
    _connect_error = exc

pytestmark = pytest.mark.skipif(
    _pg is None, reason=f"PostgreSQL not reachable: {_connect_error}"
)


@pytest.fixture(autouse=True)
def _clean_tables():
    with _pg.cursor() as cur:
        cur.execute(
            "TRUNCATE users, posts, comments, followers, likes, post_metadata "
            "RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def user_repo():
    return UserRepository(_pg)


@pytest.fixture
def post_repo():
    return PostRepository(_pg)


@pytest.fixture
def follower_repo():
    return FollowerRepository(_pg)


def _make_user(user_repo, email):
    uid = user_repo.insert(
        {"email": email, "password_hash": "x", "full_name": email.split("@")[0]}
    )
    return user_repo.find_by_id(uid)


class TestUserRepository:
    def test_insert_and_find(self, user_repo):
        doc = _make_user(user_repo, "alice@example.com")
        assert doc["email"] == "alice@example.com"
        assert doc["follower_count"] == 0
        assert doc["following_count"] == 0

    def test_find_by_email(self, user_repo):
        _make_user(user_repo, "bob@example.com")
        found = user_repo.find_by_email("bob@example.com")
        assert found is not None
        assert found["email"] == "bob@example.com"

    def test_unique_email_enforced(self, user_repo):
        _make_user(user_repo, "dup@example.com")
        with pytest.raises(psycopg2.errors.UniqueViolation):
            user_repo.insert({"email": "dup@example.com", "password_hash": "x"})


class TestFeedQuery:
    def test_feed_ordered_and_paginated(self, user_repo, post_repo):
        alice = _make_user(user_repo, "alice@example.com")
        for i in range(5):
            post_repo.insert({"user_id": alice["id"], "content": f"post {i}"})

        page1 = post_repo.feed_for_user_ids([alice["id"]], limit=2, offset=0)
        page2 = post_repo.feed_for_user_ids([alice["id"]], limit=2, offset=2)

        assert [p["content"] for p in page1] == ["post 4", "post 3"]
        assert [p["content"] for p in page2] == ["post 2", "post 1"]
        assert page1[0]["author_email"] == "alice@example.com"

    def test_feed_excludes_deleted(self, user_repo, post_repo):
        alice = _make_user(user_repo, "alice@example.com")
        pid = post_repo.insert(
            {"user_id": alice["id"], "content": "gone", "is_deleted": True}
        )
        post_repo.insert({"user_id": alice["id"], "content": "kept"})

        feed = post_repo.feed_for_user_ids([alice["id"]], limit=20)
        assert all(p["id"] != pid for p in feed)


class TestTransactionalFollow:
    def test_follow_bumps_both_counters(self, user_repo, follower_repo):
        alice = _make_user(user_repo, "alice@example.com")
        bob = _make_user(user_repo, "bob@example.com")

        assert follower_repo.follow(alice["id"], bob["id"]) is True

        alice_after = user_repo.find_by_id(alice["id"])
        bob_after = user_repo.find_by_id(bob["id"])
        assert alice_after["following_count"] == 1
        assert bob_after["follower_count"] == 1

    def test_duplicate_follow_returns_false_without_double_counting(
        self, user_repo, follower_repo
    ):
        alice = _make_user(user_repo, "alice@example.com")
        bob = _make_user(user_repo, "bob@example.com")

        assert follower_repo.follow(alice["id"], bob["id"]) is True
        assert follower_repo.follow(alice["id"], bob["id"]) is False

        bob_after = user_repo.find_by_id(bob["id"])
        assert bob_after["follower_count"] == 1  # not double-counted

    def test_unfollow_decrements_symmetrically(self, user_repo, follower_repo):
        alice = _make_user(user_repo, "alice@example.com")
        bob = _make_user(user_repo, "bob@example.com")
        follower_repo.follow(alice["id"], bob["id"])

        deleted = follower_repo.unfollow(alice["id"], bob["id"])
        assert deleted == 1

        alice_after = user_repo.find_by_id(alice["id"])
        bob_after = user_repo.find_by_id(bob["id"])
        assert alice_after["following_count"] == 0
        assert bob_after["follower_count"] == 0

    def test_self_follow_rejected_by_check_constraint(self, user_repo, follower_repo):
        alice = _make_user(user_repo, "alice@example.com")
        with pytest.raises(psycopg2.errors.CheckViolation):
            follower_repo.follow(alice["id"], alice["id"])


class TestIndexes:
    def test_followers_has_two_composite_btree_indexes(self):
        with _pg.cursor() as cur:
            cur.execute("SELECT indexdef FROM pg_indexes WHERE tablename = 'followers'")
            rows = cur.fetchall()
        composite = [
            r
            for r in rows
            if "follower_id" in r["indexdef"] and "followee_id" in r["indexdef"]
        ]
        assert len(composite) >= 2
