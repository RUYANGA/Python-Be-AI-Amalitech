"""Tests for ActivityLogService."""

from unittest.mock import MagicMock

from social_media.services.activity_log_service import ActivityLogService


class TestActivityLogService:
    def test_logs_through_when_repo_present(self):
        repo = MagicMock()
        svc = ActivityLogService(repo)

        svc.log("u1", "like", "post", "p1", {"k": "v"})

        repo.log.assert_called_once_with("u1", "like", "post", "p1", {"k": "v"})

    def test_no_op_when_repo_absent(self):
        svc = ActivityLogService()
        svc.log("u1", "like", "post", "p1")  # should not raise

    def test_default_repo_is_none(self):
        svc = ActivityLogService(None)
        svc.log("u1", "follow", "user", "u2")  # should not raise
