"""MongoDB-backed repositories. Only activity logs live in Mongo now — users,
posts, comments, followers, and likes moved to the normalized PostgreSQL
schema (see repositories/postgres_repos.py).

MongoRepository plays the same shared-CRUD role PostgresRepository plays for
the Postgres repos — generic parameterized insert/find_by_id/find/update/
delete, with each concrete class adding only its own query methods.
"""

from collections.abc import Iterable
from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from social_media.models.mongo_entities import ActivityLog
from social_media.repositories.base import IActivityLogRepository, IRepository


class MongoRepository(IRepository):
    """Shared CRUD for Mongo collections."""

    def __init__(self, collection: Collection):
        self._collection = collection

    def insert(self, document: dict) -> Any:
        """Insert a document and return its generated _id."""
        return self._collection.insert_one(document).inserted_id

    def find_by_id(self, _id: Any) -> dict | None:
        """Return the document matching the given _id, or None."""
        return self._collection.find_one({"_id": _id})

    def find(self, query: dict, limit: int = 0) -> Iterable[dict]:
        """Return documents matching the query, optionally capped by limit."""
        cursor = self._collection.find(query)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def update(self, _id: Any, changes: dict) -> int:
        """Apply changes to a document; returns the number modified."""
        return self._collection.update_one({"_id": _id}, {"$set": changes}).modified_count

    def delete(self, _id: Any) -> int:
        """Delete a document; returns the number deleted."""
        return self._collection.delete_one({"_id": _id}).deleted_count


class ActivityLogRepository(MongoRepository, IActivityLogRepository):
    """Mongo-backed audit-log collection with supporting indexes."""

    COLLECTION = "activity_logs"

    def __init__(self, db: Database):
        super().__init__(db[self.COLLECTION])
        self._collection.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        self._collection.create_index("action")

    def log(
        self,
        user_id: Any,
        action: str,
        target_type: str,
        target_id: Any | None = None,
        metadata: dict | None = None,
    ) -> Any:
        """Persist an activity entry and return its generated _id."""
        doc = ActivityLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata,
        ).to_doc()
        return self.insert(doc)
