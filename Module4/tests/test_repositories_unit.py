"""Unit tests for repository layers using fake cursors/collections (no live DBs)."""

import json
from unittest.mock import MagicMock

import psycopg2

from social_media.repositories.mongo_repos import ActivityLogRepository, MongoRepository
from social_media.repositories.postgres_metadata_repo import PostMetadataRepository
from social_media.repositories.postgres_repos import (
    CommentRepository,
    FollowerRepository,
    LikeRepository,
    PostRepository,
    UserRepository,
)


def make_pg():
    """Return (pg_mock, cursor_mock) wired through a context-manager cursor()."""
    pg = MagicMock()
    cur = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    pg.cursor.return_value = cm
    return pg, cur


# ── PostgresRepository / UserRepository ──────────────────────────────


class TestPostgresRepository:
    def test_insert(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = {"id": 7}
        result = UserRepository(pg).insert({"email": "a@b.com", "password_hash": "x"})
        assert result == 7
        cur.execute.assert_called_once()

    def test_find_by_id(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = {"id": 1, "email": "a@b.com"}
        assert UserRepository(pg).find_by_id(1) == {"id": 1, "email": "a@b.com"}

    def test_find_by_id_missing(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = None
        assert UserRepository(pg).find_by_id(999) is None

    def test_find_with_query_and_limit(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [{"id": 1}]
        rows = UserRepository(pg).find({"email": "a@b.com"}, limit=5)
        assert rows == [{"id": 1}]
        assert "LIMIT 5" in cur.execute.call_args[0][0]

    def test_find_no_query_no_limit(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [{"id": 1}]
        rows = UserRepository(pg).find({})
        assert rows == [{"id": 1}]
        assert "WHERE" not in cur.execute.call_args[0][0]

    def test_update(self):
        pg, cur = make_pg()
        cur.rowcount = 1
        assert UserRepository(pg).update(3, {"full_name": "New"}) == 1
        assert list(cur.execute.call_args[0][1]) == ["New", 3]

    def test_delete(self):
        pg, cur = make_pg()
        cur.rowcount = 1
        assert UserRepository(pg).delete(3) == 1

    def test_find_by_email(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = {"id": 1, "email": "a@b.com"}
        assert UserRepository(pg).find_by_email("a@b.com")["email"] == "a@b.com"


# ── PostgresCompositeRepository / FollowerRepository / LikeRepository ─


class TestCompositeRepository:
    def test_key_where(self):
        pg, _ = make_pg()
        assert FollowerRepository(pg)._key_where() == "follower_id = %s AND followee_id = %s"

    def test_composite_insert(self):
        pg, cur = make_pg()
        result = FollowerRepository(pg).insert({"follower_id": 1, "followee_id": 2})
        assert result == (1, 2)
        cur.execute.assert_called_once()

    def test_composite_find_by_id(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = {"follower_id": 1, "followee_id": 2}
        row = FollowerRepository(pg).find_by_id((1, 2))
        assert row["follower_id"] == 1

    def test_composite_find(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [{"follower_id": 1}]
        rows = FollowerRepository(pg).find({"follower_id": 1}, limit=10)
        assert rows == [{"follower_id": 1}]
        assert "LIMIT 10" in cur.execute.call_args[0][0]

    def test_composite_find_no_query(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = []
        assert FollowerRepository(pg).find({}) == []

    def test_composite_update(self):
        pg, cur = make_pg()
        cur.rowcount = 1
        assert FollowerRepository(pg).update((1, 2), {"created_at": "now"}) == 1

    def test_composite_delete(self):
        pg, cur = make_pg()
        cur.rowcount = 1
        assert FollowerRepository(pg).delete((1, 2)) == 1


class TestFollowerRepository:
    def test_follow_success(self):
        pg, cur = make_pg()
        assert FollowerRepository(pg).follow(1, 2) is True

    def test_follow_duplicate(self):
        pg, cur = make_pg()
        cur.execute.side_effect = psycopg2.errors.UniqueViolation("dup")
        assert FollowerRepository(pg).follow(1, 2) is False

    def test_unfollow_with_deleted_edge(self):
        pg, cur = make_pg()
        cur.rowcount = 1
        assert FollowerRepository(pg).unfollow(1, 2) == 1
        assert "DELETE FROM followers" in cur.execute.call_args[0][0]

    def test_unfollow_no_edge(self):
        pg, cur = make_pg()
        cur.rowcount = 0
        assert FollowerRepository(pg).unfollow(1, 2) == 0
        assert cur.execute.call_count == 1

    def test_followees_of(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [{"followee_id": 2}, {"followee_id": 3}]
        assert FollowerRepository(pg).followees_of(1) == [2, 3]

    def test_followers_of(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [{"follower_id": 5}]
        assert FollowerRepository(pg).followers_of(2) == [5]


class TestLikeRepository:
    def test_exists_true(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = {"?column?": 1}
        assert LikeRepository(pg).exists(1, 2) is True

    def test_exists_false(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = None
        assert LikeRepository(pg).exists(1, 2) is False

    def test_remove(self):
        pg, cur = make_pg()
        cur.rowcount = 1
        assert LikeRepository(pg).remove(1, 2) == 1


# ── PostRepository / CommentRepository ───────────────────────────────


class TestPostRepository:
    def test_feed_for_user_ids(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [{"id": 1}]
        rows = PostRepository(pg).feed_for_user_ids([1, 2], limit=5, offset=10)
        assert rows == [{"id": 1}]
        assert list(cur.execute.call_args[0][1]) == [[1, 2], 10, 15]

    def test_trending(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [{"id": 1}]
        assert PostRepository(pg).trending(limit=7, since_hours=24) == [{"id": 1}]

    def test_increment_like_count(self):
        pg, cur = make_pg()
        PostRepository(pg).increment_like_count(4, 1)
        assert list(cur.execute.call_args[0][1]) == [1, 4]

    def test_increment_comment_count(self):
        pg, cur = make_pg()
        PostRepository(pg).increment_comment_count(4, -1)
        assert list(cur.execute.call_args[0][1]) == [-1, 4]


class TestCommentRepository:
    def test_for_post(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [{"id": 1, "content": "hi"}]
        rows = CommentRepository(pg).for_post(9)
        assert rows == [{"id": 1, "content": "hi"}]
        assert cur.execute.call_args[0][1] == (9,)


# ── PostMetadataRepository ───────────────────────────────────────────


class TestPostMetadataRepository:
    def test_upsert_new(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = None
        PostMetadataRepository(pg).upsert(1, tags=["a"], location="Accra")
        args = cur.execute.call_args[0]
        assert json.loads(args[1][1]) == {"tags": ["a"], "location": "Accra"}

    def test_upsert_merges_existing(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = {"metadata": {"tags": ["old"], "location": "Kumasi"}}
        PostMetadataRepository(pg).upsert(1, tags=["new"])
        args = cur.execute.call_args[0]
        assert json.loads(args[1][1]) == {"tags": ["new"], "location": "Kumasi"}

    def test_find_by_id(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = {"metadata": {"tags": ["a"]}}
        assert PostMetadataRepository(pg).find_by_id(1) == {"tags": ["a"]}

    def test_find_by_id_missing(self):
        pg, cur = make_pg()
        cur.fetchone.return_value = None
        assert PostMetadataRepository(pg).find_by_id(1) is None

    def test_find_many_empty(self):
        pg, _ = make_pg()
        assert PostMetadataRepository(pg).find_many([]) == {}

    def test_find_many(self):
        pg, cur = make_pg()
        cur.fetchall.return_value = [
            {"post_id": 1, "metadata": {"tags": ["a"]}},
            {"post_id": 2, "metadata": {"tags": ["b"]}},
        ]
        result = PostMetadataRepository(pg).find_many([1, 2])
        assert result == {1: {"tags": ["a"]}, 2: {"tags": ["b"]}}

    def test_delete(self):
        pg, cur = make_pg()
        PostMetadataRepository(pg).delete(1)
        assert cur.execute.call_args[0][1] == (1,)


# ── MongoRepository / ActivityLogRepository ──────────────────────────


class TestMongoRepository:
    def test_insert(self):
        col = MagicMock()
        col.insert_one.return_value.inserted_id = "obj1"
        assert MongoRepository(col).insert({"a": 1}) == "obj1"

    def test_find_by_id(self):
        col = MagicMock()
        col.find_one.return_value = {"_id": "obj1"}
        assert MongoRepository(col).find_by_id("obj1") == {"_id": "obj1"}

    def test_find_without_limit(self):
        col = MagicMock()
        col.find.return_value = [{"a": 1}]
        assert MongoRepository(col).find({"a": 1}) == [{"a": 1}]

    def test_find_with_limit(self):
        col = MagicMock()
        cursor = MagicMock()
        cursor.limit.return_value = [{"a": 1}]
        col.find.return_value = cursor
        assert MongoRepository(col).find({"a": 1}, limit=3) == [{"a": 1}]
        cursor.limit.assert_called_once_with(3)

    def test_update(self):
        col = MagicMock()
        col.update_one.return_value.modified_count = 1
        assert MongoRepository(col).update("obj1", {"b": 2}) == 1

    def test_delete(self):
        col = MagicMock()
        col.delete_one.return_value.deleted_count = 1
        assert MongoRepository(col).delete("obj1") == 1


class TestActivityLogRepository:
    def test_init_creates_indexes(self):
        db = MagicMock()
        col = MagicMock()
        db.__getitem__.return_value = col

        ActivityLogRepository(db)

        assert col.create_index.call_count == 2

    def test_log(self):
        db = MagicMock()
        col = MagicMock()
        col.insert_one.return_value.inserted_id = "log1"
        db.__getitem__.return_value = col

        repo = ActivityLogRepository(db)
        result = repo.log("u1", "like", "post", "p1", {"k": "v"})

        assert result == "log1"
        doc = col.insert_one.call_args[0][0]
        assert doc["user_id"] == "u1"
        assert doc["action"] == "like"
        assert doc["target_type"] == "post"
        assert doc["target_id"] == "p1"
        assert doc["metadata"] == {"k": "v"}
