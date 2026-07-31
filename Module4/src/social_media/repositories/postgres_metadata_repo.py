"""PostgreSQL repository for post metadata (tags, location) stored as JSONB."""

import json
from typing import Any

from social_media.database.postgres_connection import PostgresConnection


class PostMetadataRepository:
    """CRUD for post_metadata table backed by PostgreSQL JSONB."""

    def __init__(self, pg_connection: PostgresConnection):
        self._pg_connection = pg_connection

    def upsert(
        self, post_id: int, tags: list[str] | None = None, location: str | None = None
    ) -> None:
        existing = self.find_by_id(post_id) or {}
        metadata = {
            "tags": tags if tags is not None else existing.get("tags", []),
            "location": location if location is not None else existing.get("location"),
        }
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO post_metadata (post_id, metadata)
                VALUES (%s, %s)
                ON CONFLICT (post_id)
                DO UPDATE SET metadata = EXCLUDED.metadata
                """,
                (post_id, json.dumps(metadata)),
            )

    def find_by_id(self, post_id: int) -> dict[str, Any] | None:
        with self._pg_connection.cursor() as cursor:
            cursor.execute("SELECT metadata FROM post_metadata WHERE post_id = %s", (post_id,))
            row = cursor.fetchone()
            return row["metadata"] if row else None

    def find_many(self, post_ids: list[int]) -> dict[int, dict]:
        if not post_ids:
            return {}
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                "SELECT post_id, metadata FROM post_metadata WHERE post_id = ANY(%s)",
                (post_ids,),
            )
            return {row["post_id"]: row["metadata"] for row in cursor.fetchall()}

    def delete(self, post_id: int) -> None:
        with self._pg_connection.cursor() as cursor:
            cursor.execute("DELETE FROM post_metadata WHERE post_id = %s", (post_id,))
