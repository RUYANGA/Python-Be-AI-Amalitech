"""Tests for MongoDB-backed domain model entities."""

from social_media.models.mongo_entities import ActivityLog


class TestActivityLog:
    def test_to_doc_without_id(self):
        log = ActivityLog(user_id="u1", action="like", target_type="post", target_id="p1")
        doc = log.to_doc()
        assert doc["user_id"] == "u1"
        assert doc["action"] == "like"
        assert doc["target_type"] == "post"
        assert doc["target_id"] == "p1"
        assert "_id" not in doc

    def test_to_doc_with_id(self):
        log = ActivityLog(user_id="u1", action="like", target_type="post", _id="log1")
        assert log.to_doc()["_id"] == "log1"

    def test_defaults(self):
        log = ActivityLog(user_id="u1", action="follow", target_type="user")
        assert log.target_id is None
        assert log.metadata is None
