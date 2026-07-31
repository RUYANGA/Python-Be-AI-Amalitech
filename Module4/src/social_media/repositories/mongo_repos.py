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
        self._col = collection

    def insert(self, document: dict) -> Any:
        return self._col.insert_one(document).inserted_id

    def find_by_id(self, _id: Any) -> dict | None:
        return self._col.find_one({"_id": _id})

    def find(self, query: dict, limit: int = 0) -> Iterable[dict]:
        cursor = self._col.find(query)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def update(self, _id: Any, changes: dict) -> int:
        return self._col.update_one({"_id": _id}, {"$set": changes}).modified_count

    def delete(self, _id: Any) -> int:
        return self._col.delete_one({"_id": _id}).deleted_count


class ActivityLogRepository(MongoRepository, IActivityLogRepository):
    COLLECTION = "activity_logs"

    def __init__(self, db: Database):
        super().__init__(db[self.COLLECTION])
        self._col.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        self._col.create_index("action")

    def log(
        self,
        user_id: Any,
        action: str,
        target_type: str,
        target_id: Any | None = None,
        metadata: dict | None = None,
    ) -> Any:
        doc = ActivityLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata,
        ).to_doc()
        return self.insert(doc)
