"""Tests for PostService."""

from unittest.mock import MagicMock

import pytest

from social_media.exceptions import EmptyPostContentError
from social_media.services.post_service import PostService
from tests.conftest import fake_id


class TestCreate:
    def test_create_post(self, post_svc: PostService, post_repo: MagicMock):
        pid = fake_id()
        post_repo.insert.return_value = pid
        post_repo.find_by_id.return_value = {
            "id": pid,
            "user_id": "u1",
            "content": "Hello!",
        }

        result = post_svc.create("u1", "Hello!")
        assert result["content"] == "Hello!"
        post_repo.insert.assert_called_once()

    def test_empty_content_raises(self, post_svc: PostService):
        with pytest.raises(EmptyPostContentError, match="cannot be empty"):
            post_svc.create("u1", "   ")

    def test_whitespace_only_raises(self, post_svc: PostService):
        with pytest.raises(EmptyPostContentError):
            post_svc.create("u1", "\t\n ")


class TestUpdate:
    def test_update_content(self, post_svc: PostService, post_repo: MagicMock):
        pid = fake_id()
        post_repo.find_by_id.return_value = {
            "id": pid,
            "user_id": "u1",
            "content": "New content",
        }
        result = post_svc.update(pid, "New content")
        assert result["content"] == "New content"
        post_repo.update.assert_called_once_with(pid, {"content": "New content"})

    def test_update_empty_raises(self, post_svc: PostService):
        with pytest.raises(EmptyPostContentError, match="cannot be empty"):
            post_svc.update(fake_id(), "   ")

    def test_update_whitespace_only_raises(self, post_svc: PostService):
        with pytest.raises(EmptyPostContentError):
            post_svc.update(fake_id(), "\n\t")


class TestSoftDelete:
    def test_soft_delete(self, post_svc: PostService, post_repo: MagicMock):
        pid = fake_id()
        post_svc.soft_delete(pid)
        post_repo.update.assert_called_once_with(pid, {"is_deleted": True})


class TestTimeline:
    def test_timeline_includes_own_posts(
        self, post_svc: PostService, post_repo: MagicMock, follower_repo: MagicMock
    ):
        uid = fake_id()
        follower_repo.followees_of.return_value = []

        posts = [
            {"id": fake_id(), "user_id": uid, "content": "My post"},
        ]
        post_repo.feed_for_user_ids.return_value = posts

        result = post_svc.timeline_for(uid)
        assert len(result) == 1
        post_repo.feed_for_user_ids.assert_called_once()

    def test_timeline_includes_followees(
        self, post_svc: PostService, post_repo: MagicMock, follower_repo: MagicMock
    ):
        uid = fake_id()
        followee_id = fake_id()
        follower_repo.followees_of.return_value = [followee_id]

        posts = [
            {"id": fake_id(), "user_id": followee_id, "content": "Followee post"},
        ]
        post_repo.feed_for_user_ids.return_value = posts

        result = post_svc.timeline_for(uid)
        assert len(result) == 1
        # Verify both user and followees are included in the query
        called_ids = post_repo.feed_for_user_ids.call_args[0][0]
        assert uid in called_ids
        assert followee_id in called_ids

    def test_timeline_empty_when_no_followees(
        self, post_svc: PostService, post_repo: MagicMock, follower_repo: MagicMock
    ):
        follower_repo.followees_of.return_value = []
        post_repo.feed_for_user_ids.return_value = []

        result = post_svc.timeline_for(fake_id())
        assert result == []

    def test_timeline_respects_limit(
        self, post_svc: PostService, post_repo: MagicMock, follower_repo: MagicMock
    ):
        follower_repo.followees_of.return_value = []
        post_repo.feed_for_user_ids.return_value = []

        post_svc.timeline_for(fake_id(), limit=5)
        assert post_repo.feed_for_user_ids.call_args[1]["limit"] == 5
