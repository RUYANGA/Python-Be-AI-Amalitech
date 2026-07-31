"""Tests for PostgreSQL-backed domain model entities."""

from datetime import datetime

from social_media.models.postgres_entities import Comment, Follower, Like, Post, User


class TestUser:
    def test_to_doc_without_id(self):
        u = User(email="a@b.com", password_hash="hash", full_name="Alice")
        doc = u.to_doc()
        assert doc["email"] == "a@b.com"
        assert doc["password_hash"] == "hash"
        assert doc["full_name"] == "Alice"
        assert "id" not in doc

    def test_to_doc_with_id(self):
        uid = 42
        u = User(email="a@b.com", password_hash="hash", id=uid)
        doc = u.to_doc()
        assert doc["id"] == uid

    def test_defaults(self):
        u = User(email="a@b.com", password_hash="h")
        assert u.is_active is True
        assert u.full_name is None
        assert u.bio is None
        assert isinstance(u.created_at, datetime)


class TestPost:
    def test_to_doc_without_id(self):
        p = Post(user_id="u1", content="Hello")
        doc = p.to_doc()
        assert doc["user_id"] == "u1"
        assert doc["content"] == "Hello"
        assert doc["like_count"] == 0
        assert doc["is_deleted"] is False
        assert "id" not in doc

    def test_to_doc_with_id(self):
        p = Post(user_id="u1", content="Hello", id=7)
        assert p.to_doc()["id"] == 7


class TestComment:
    def test_to_doc(self):
        c = Comment(post_id="p1", user_id="u1", content="Nice!")
        doc = c.to_doc()
        assert doc["post_id"] == "p1"
        assert doc["user_id"] == "u1"
        assert doc["parent_comment_id"] is None
        assert "id" not in doc

    def test_with_parent(self):
        c = Comment(post_id="p1", user_id="u1", content="Reply", parent_comment_id="c1")
        assert c.to_doc()["parent_comment_id"] == "c1"


class TestFollower:
    def test_to_doc(self):
        f = Follower(follower_id="u1", followee_id="u2")
        doc = f.to_doc()
        assert doc["follower_id"] == "u1"
        assert doc["followee_id"] == "u2"
        assert "created_at" in doc


class TestLike:
    def test_to_doc(self):
        lk = Like(user_id="u1", post_id="p1")
        doc = lk.to_doc()
        assert doc["user_id"] == "u1"
        assert doc["post_id"] == "p1"
        assert "created_at" in doc
