"""Tests for LikeService, CommentService, and FollowService."""

from unittest.mock import MagicMock

import pytest

from social_media.exceptions import EmptyCommentError, SelfFollowError
from social_media.services.interaction_service import (
    CommentService,
    FollowService,
    LikeService,
)
from tests.conftest import fake_id

# ── LikeService ─────────────────────────────────────────────────────


class TestLikeService:
    def test_like(self, like_svc: LikeService, like_repo: MagicMock, post_repo: MagicMock):
        uid, pid = fake_id(), fake_id()
        like_repo.exists.return_value = False
        like_repo.insert.return_value = fake_id()

        result = like_svc.like(uid, pid)
        assert result is True
        like_repo.insert.assert_called_once()
        post_repo.increment_like_count.assert_called_once_with(pid, 1)

    def test_like_duplicate(
        self, like_svc: LikeService, like_repo: MagicMock, post_repo: MagicMock
    ):
        like_repo.exists.return_value = True
        result = like_svc.like(fake_id(), fake_id())
        assert result is False
        like_repo.insert.assert_not_called()

    def test_unlike(self, like_svc: LikeService, like_repo: MagicMock, post_repo: MagicMock):
        uid, pid = fake_id(), fake_id()
        like_repo.remove.return_value = 1
        result = like_svc.unlike(uid, pid)
        assert result is True
        post_repo.increment_like_count.assert_called_once_with(pid, -1)

    def test_unlike_not_liked(
        self, like_svc: LikeService, like_repo: MagicMock, post_repo: MagicMock
    ):
        like_repo.remove.return_value = 0
        result = like_svc.unlike(fake_id(), fake_id())
        assert result is False

    def test_post_snippet_short_content(self, like_svc: LikeService, post_repo: MagicMock):
        pid = fake_id()
        post_repo.find_by_id.return_value = {"id": pid, "content": "short"}
        assert like_svc._post_snippet(pid) == '"short"'

    def test_post_snippet_long_content(self, like_svc: LikeService, post_repo: MagicMock):
        pid = fake_id()
        post_repo.find_by_id.return_value = {
            "id": pid,
            "content": "x" * 100,
        }
        assert like_svc._post_snippet(pid) == '"' + "x" * 40 + '..."'

    def test_post_snippet_missing_post(self, like_svc: LikeService, post_repo: MagicMock):
        pid = fake_id()
        post_repo.find_by_id.return_value = None
        assert like_svc._post_snippet(pid) == str(pid)


# ── CommentService ──────────────────────────────────────────────────


class TestCommentService:
    def test_add_comment(
        self, comment_svc: CommentService, comment_repo: MagicMock, post_repo: MagicMock
    ):
        pid = fake_id()
        uid = fake_id()
        cid = fake_id()
        comment_repo.insert.return_value = cid
        comment_repo.find_by_id.return_value = {
            "_id": cid,
            "post_id": pid,
            "user_id": uid,
            "content": "Nice!",
        }

        result = comment_svc.add(pid, uid, "Nice!")
        assert result["content"] == "Nice!"
        post_repo.increment_comment_count.assert_called_once_with(pid, 1)

    def test_add_comment_empty_content(self, comment_svc: CommentService):
        with pytest.raises(EmptyCommentError, match="cannot be empty"):
            comment_svc.add(fake_id(), fake_id(), "")

    def test_add_comment_with_parent(
        self, comment_svc: CommentService, comment_repo: MagicMock, post_repo: MagicMock
    ):
        parent_id = fake_id()
        comment_svc.add(fake_id(), fake_id(), "Reply", parent_comment_id=parent_id)
        inserted = comment_repo.insert.call_args[0][0]
        assert inserted["parent_comment_id"] == parent_id

    def test_for_post(self, comment_svc: CommentService, comment_repo: MagicMock):
        pid = fake_id()
        comment_repo.for_post.return_value = [{"_id": fake_id(), "content": "C1"}]
        results = comment_svc.for_post(pid)
        assert len(results) == 1
        comment_repo.for_post.assert_called_once_with(pid)


# ── FollowService ───────────────────────────────────────────────────


class TestFollowService:
    def test_follow(self, follow_svc: FollowService, follower_repo: MagicMock):
        follower_repo.follow.return_value = True
        result = follow_svc.follow(fake_id(), fake_id())
        assert result is True

    def test_follow_duplicate(self, follow_svc: FollowService, follower_repo: MagicMock):
        follower_repo.follow.return_value = False
        result = follow_svc.follow(fake_id(), fake_id())
        assert result is False

    def test_follow_self(self, follow_svc: FollowService, follower_repo: MagicMock):
        uid = fake_id()
        with pytest.raises(SelfFollowError, match="Cannot follow yourself"):
            follow_svc.follow(uid, uid)

    def test_unfollow(self, follow_svc: FollowService, follower_repo: MagicMock):
        follower_repo.unfollow.return_value = 1
        result = follow_svc.unfollow(fake_id(), fake_id())
        assert result is True

    def test_unfollow_not_following(self, follow_svc: FollowService, follower_repo: MagicMock):
        follower_repo.unfollow.return_value = 0
        result = follow_svc.unfollow(fake_id(), fake_id())
        assert result is False
