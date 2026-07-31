"""Shared fixtures and helpers for tests."""

import itertools
import sys
from pathlib import Path

# Ensure src/ and the project root are on the path
_root = str(Path(__file__).resolve().parent.parent)
_src = str(Path(_root) / "src")
for p in [_root, _src]:
    if p not in sys.path:
        sys.path.insert(0, p)

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from social_media.services.interaction_service import (
    CommentService,
    FollowService,
    LikeService,
)
from social_media.services.post_service import PostService
from social_media.services.user_service import UserService
from social_media.utils.security import PasswordHasher

# ── Fake surrogate-key generator (mirrors Postgres BIGSERIAL ids) ────

_id_counter = itertools.count(1)


def fake_id() -> int:
    return next(_id_counter)


# ── Mock repository factories ───────────────────────────────────────


def make_user_repo(users: list[dict] | None = None) -> MagicMock:
    users = users or []
    repo = MagicMock()
    repo.find_by_email.return_value = None
    repo.insert.return_value = fake_id()
    repo.find_by_id.return_value = {"id": fake_id(), "email": "test@example.com"}
    repo.find.return_value = users
    return repo


def make_post_repo(posts: list[dict] | None = None) -> MagicMock:
    posts = posts or []
    repo = MagicMock()
    repo.insert.return_value = fake_id()
    repo.find_by_id.return_value = {
        "id": fake_id(),
        "user_id": fake_id(),
        "content": "test",
    }
    repo.find.return_value = posts
    repo.feed_for_user_ids.return_value = posts
    repo.trending.return_value = []
    repo.increment_like_count = MagicMock()
    repo.increment_comment_count = MagicMock()
    return repo


def make_follower_repo() -> MagicMock:
    repo = MagicMock()
    repo.follow.return_value = True
    repo.followees_of.return_value = []
    repo.followers_of.return_value = []
    repo.unfollow.return_value = 0
    return repo


def make_like_repo() -> MagicMock:
    repo = MagicMock()
    repo.exists.return_value = False
    repo.insert.return_value = fake_id()
    repo.remove.return_value = 0
    return repo


def make_comment_repo() -> MagicMock:
    repo = MagicMock()
    repo.insert.return_value = fake_id()
    repo.find_by_id.return_value = {"id": fake_id(), "content": "test"}
    repo.for_post.return_value = []
    return repo


def make_metadata_repo() -> MagicMock:
    repo = MagicMock()
    repo.find_many.return_value = {}
    repo.find_by_id.return_value = None
    return repo


# ── Creates a realistic user document ────────────────────────────────


def user_doc(
    email: str = "test@example.com",
    full_name: str = "Test User",
    **overrides: Any,
) -> dict:
    doc = {
        "id": fake_id(),
        "email": email,
        "password_hash": PasswordHasher().hash("password123"),
        "full_name": full_name,
        "bio": None,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    doc.update(overrides)
    return doc


def post_doc(user_id: Any, content: str = "Test post", **overrides: Any) -> dict:
    doc = {
        "id": fake_id(),
        "user_id": user_id,
        "content": content,
        "like_count": 0,
        "comment_count": 0,
        "is_deleted": False,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    doc.update(overrides)
    return doc


# ── Mock build_services helper for CLI tests ─────────────────────────

CLI_SERVICE_KEYS = ["users", "posts", "likes", "comments", "follows", "metadata_repo"]


def mock_cli_services(**overrides: MagicMock) -> dict[str, MagicMock]:
    svcs = {
        "users": MagicMock(),
        "posts": MagicMock(),
        "likes": MagicMock(),
        "comments": MagicMock(),
        "follows": MagicMock(),
        "metadata_repo": make_metadata_repo(),
    }
    svcs.update(overrides)
    return svcs


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def user_repo() -> MagicMock:
    return make_user_repo()


@pytest.fixture
def post_repo() -> MagicMock:
    return make_post_repo()


@pytest.fixture
def follower_repo() -> MagicMock:
    return make_follower_repo()


@pytest.fixture
def like_repo() -> MagicMock:
    return make_like_repo()


@pytest.fixture
def comment_repo() -> MagicMock:
    return make_comment_repo()


@pytest.fixture
def user_svc(user_repo: MagicMock, hasher: PasswordHasher) -> UserService:
    return UserService(user_repo, hasher)


@pytest.fixture
def post_svc(post_repo: MagicMock, follower_repo: MagicMock) -> PostService:
    return PostService(post_repo, follower_repo)


@pytest.fixture
def like_svc(like_repo: MagicMock, post_repo: MagicMock) -> LikeService:
    return LikeService(like_repo, post_repo)


@pytest.fixture
def comment_svc(comment_repo: MagicMock, post_repo: MagicMock) -> CommentService:
    return CommentService(comment_repo, post_repo)


@pytest.fixture
def follow_svc(follower_repo: MagicMock) -> FollowService:
    return FollowService(follower_repo)
