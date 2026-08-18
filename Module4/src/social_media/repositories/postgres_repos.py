"""Concrete PostgreSQL repositories, one per table, mirroring the 3NF schema.

PostgresRepository/PostgresCompositeRepository play the same shared-CRUD
role MongoRepository plays for the Mongo repos — generic parameterized
insert/find_by_id/find/update/delete, with each concrete class adding only
its own query methods.
"""

import json
from collections.abc import Iterable
from typing import Any

import psycopg2

from social_media.database.postgres_connection import PostgresConnection
from social_media.repositories.base import (
    ICommentRepository,
    IFollowerRepository,
    ILikeRepository,
    IPostRepository,
    IRepository,
    IUserRepository,
)


class PostgresRepository(IRepository):
    """Shared CRUD for tables with a single-column primary key."""

    TABLE: str = ""
    ID_COLUMN: str = "id"

    def __init__(self, pg_connection: PostgresConnection):
        self._pg_connection = pg_connection

    def insert(self, document: dict) -> Any:
        """Insert a document and return its generated id."""
        columns = list(document.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        columns_sql = ", ".join(columns)
        sql = (
            f"INSERT INTO {self.TABLE} ({columns_sql}) VALUES ({placeholders}) "
            f"RETURNING {self.ID_COLUMN}"
        )
        with self._pg_connection.cursor() as cursor:
            cursor.execute(sql, list(document.values()))
            row = cursor.fetchone()
            assert row is not None, "INSERT RETURNING should always yield a row"
            return row[self.ID_COLUMN]

    def find_by_id(self, _id: Any) -> dict | None:
        """Return the row for an id, or None."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {self.TABLE} WHERE {self.ID_COLUMN} = %s", (_id,))
            return cursor.fetchone()

    def find(self, query: dict, limit: int = 0) -> Iterable[dict]:
        """Return rows matching a query, optionally capped by limit."""
        where_sql, params = "", []
        if query:
            where_sql = "WHERE " + " AND ".join(f"{col} = %s" for col in query)
            params = list(query.values())
        limit_sql = f" LIMIT {int(limit)}" if limit else ""
        sql = f"SELECT * FROM {self.TABLE} {where_sql} ORDER BY {self.ID_COLUMN}{limit_sql}"
        with self._pg_connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def update(self, _id: Any, changes: dict) -> int:
        """Apply changes to a row and return the rows affected."""
        set_sql = ", ".join(f"{col} = %s" for col in changes)
        sql = f"UPDATE {self.TABLE} SET {set_sql} WHERE {self.ID_COLUMN} = %s"
        with self._pg_connection.cursor() as cursor:
            cursor.execute(sql, [*changes.values(), _id])
            return cursor.rowcount

    def delete(self, _id: Any) -> int:
        """Delete a row and return the rows affected."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {self.TABLE} WHERE {self.ID_COLUMN} = %s", (_id,))
            return cursor.rowcount


class PostgresCompositeRepository(IRepository):
    """Shared CRUD for tables keyed by a (col_a, col_b) composite PK."""

    TABLE: str = ""
    KEY_COLUMNS: tuple[str, str] = ("", "")

    def __init__(self, pg_connection: PostgresConnection):
        self._pg_connection = pg_connection

    def _key_where(self) -> str:
        """Return the composite-key equality fragment for WHERE clauses."""
        key_a, key_b = self.KEY_COLUMNS
        return f"{key_a} = %s AND {key_b} = %s"

    def insert(self, document: dict) -> Any:
        """Insert a document and return its composite key pair."""
        columns = list(document.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        columns_sql = ", ".join(columns)
        sql = f"INSERT INTO {self.TABLE} ({columns_sql}) VALUES ({placeholders})"
        with self._pg_connection.cursor() as cursor:
            cursor.execute(sql, list(document.values()))
        key_a, key_b = self.KEY_COLUMNS
        return (document[key_a], document[key_b])

    def find_by_id(self, _id: tuple) -> dict | None:
        """Return the row for a composite key, or None."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {self.TABLE} WHERE {self._key_where()}", _id)
            return cursor.fetchone()

    def find(self, query: dict, limit: int = 0) -> Iterable[dict]:
        """Return rows matching a query, optionally capped by limit."""
        where_sql, params = "", []
        if query:
            where_sql = "WHERE " + " AND ".join(f"{col} = %s" for col in query)
            params = list(query.values())
        limit_sql = f" LIMIT {int(limit)}" if limit else ""
        sql = f"SELECT * FROM {self.TABLE} {where_sql} ORDER BY created_at{limit_sql}"
        with self._pg_connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def update(self, _id: tuple, changes: dict) -> int:
        """Apply changes to a row and return the rows affected."""
        set_sql = ", ".join(f"{col} = %s" for col in changes)
        sql = f"UPDATE {self.TABLE} SET {set_sql} WHERE {self._key_where()}"
        with self._pg_connection.cursor() as cursor:
            cursor.execute(sql, [*changes.values(), *_id])
            return cursor.rowcount

    def delete(self, _id: tuple) -> int:
        """Delete a row and return the rows affected."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {self.TABLE} WHERE {self._key_where()}", _id)
            return cursor.rowcount


class UserRepository(PostgresRepository, IUserRepository):
    """Users table backed by PostgreSQL."""

    TABLE = "users"

    def find_by_email(self, email: str) -> dict | None:
        """Look up a user doc by email address."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()


class PostRepository(PostgresRepository, IPostRepository):
    """Posts table backed by PostgreSQL — adds feed/trending/counter queries."""

    TABLE = "posts"

    # CTE + JOIN + ROW_NUMBER(): ranks each followee/own post by recency,
    # then slices the requested page. Backed by idx_posts_user_created.
    FEED_QUERY = """
        WITH ranked_feed AS (
            SELECT
                p.id, p.user_id, p.content, p.like_count, p.comment_count,
                p.created_at, p.updated_at,
                u.full_name AS author_name, u.email AS author_email,
                ROW_NUMBER() OVER (ORDER BY p.created_at DESC, p.id DESC) AS rn
            FROM posts p
            JOIN users u ON u.id = p.user_id
            WHERE p.user_id = ANY(%s) AND NOT p.is_deleted
        )
        SELECT id, user_id, content, like_count, comment_count, created_at, updated_at,
               author_name, author_email
        FROM ranked_feed
        WHERE rn > %s AND rn <= %s
        ORDER BY rn
    """

    TRENDING_QUERY = """
        SELECT p.id, p.user_id, p.content, p.like_count, p.comment_count, p.created_at,
               u.full_name AS author_name, u.email AS author_email,
               (p.like_count * 2 + p.comment_count) AS score
        FROM posts p
        JOIN users u ON u.id = p.user_id
        WHERE NOT p.is_deleted AND p.created_at > now() - (%s || ' hours')::interval
        ORDER BY score DESC, p.created_at DESC
        LIMIT %s
    """

    def feed_for_user_ids(self, user_ids: list[Any], limit: int = 20, offset: int = 0) -> list:
        """Return a page of non-deleted posts by the given authors, newest first."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(self.FEED_QUERY, (user_ids, offset, offset + limit))
            return cursor.fetchall()

    def trending(self, limit: int = 20, since_hours: int = 168) -> list:
        """Return recent posts ordered by engagement score, highest first."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(self.TRENDING_QUERY, (since_hours, limit))
            return cursor.fetchall()

    def increment_like_count(self, post_id: Any, delta: int) -> None:
        """Adjust a post's like counter by delta."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                "UPDATE posts SET like_count = like_count + %s WHERE id = %s",
                (delta, post_id),
            )

    def increment_comment_count(self, post_id: Any, delta: int) -> None:
        """Adjust a post's comment counter by delta."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                "UPDATE posts SET comment_count = comment_count + %s WHERE id = %s",
                (delta, post_id),
            )


class CommentRepository(PostgresRepository, ICommentRepository):
    """Comments table backed by PostgreSQL."""

    TABLE = "comments"

    def for_post(self, post_id: Any) -> list:
        """Return the non-deleted comments on a post, oldest first."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM comments WHERE post_id = %s AND NOT is_deleted "
                "ORDER BY created_at ASC",
                (post_id,),
            )
            return cursor.fetchall()


class FollowerRepository(PostgresCompositeRepository, IFollowerRepository):
    """Followers join table — composite (follower_id, followee_id) primary key."""

    TABLE = "followers"
    KEY_COLUMNS = ("follower_id", "followee_id")

    def follow(self, follower_id: Any, followee_id: Any) -> bool:
        """Insert the edge and bump both counters atomically. False on duplicate."""
        try:
            with self._pg_connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO followers (follower_id, followee_id) VALUES (%s, %s)",
                    (follower_id, followee_id),
                )
                cursor.execute(
                    "UPDATE users SET following_count = following_count + 1 WHERE id = %s",
                    (follower_id,),
                )
                cursor.execute(
                    "UPDATE users SET follower_count = follower_count + 1 WHERE id = %s",
                    (followee_id,),
                )
            return True
        except psycopg2.errors.UniqueViolation:
            return False

    def unfollow(self, follower_id: Any, followee_id: Any) -> int:
        """Delete the follow edge and decrement both counters; returns rows affected."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM followers WHERE follower_id = %s AND followee_id = %s",
                (follower_id, followee_id),
            )
            deleted = cursor.rowcount
            if deleted:
                cursor.execute(
                    "UPDATE users SET following_count = GREATEST(following_count - 1, 0) "
                    "WHERE id = %s",
                    (follower_id,),
                )
                cursor.execute(
                    "UPDATE users SET follower_count = GREATEST(follower_count - 1, 0) "
                    "WHERE id = %s",
                    (followee_id,),
                )
            return deleted

    def followees_of(self, user_id: Any) -> list[Any]:
        """Return the ids of the users the given user follows."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute("SELECT followee_id FROM followers WHERE follower_id = %s", (user_id,))
            return [row["followee_id"] for row in cursor.fetchall()]

    def followers_of(self, user_id: Any) -> list[Any]:
        """Return the ids of the users following the given user."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute("SELECT follower_id FROM followers WHERE followee_id = %s", (user_id,))
            return [row["follower_id"] for row in cursor.fetchall()]


class LikeRepository(PostgresCompositeRepository, ILikeRepository):
    """Likes join table — composite (user_id, post_id) primary key."""

    TABLE = "likes"
    KEY_COLUMNS = ("user_id", "post_id")

    def exists(self, user_id: Any, post_id: Any) -> bool:
        """Return True if the user has already liked the post."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM likes WHERE user_id = %s AND post_id = %s",
                (user_id, post_id),
            )
            return cursor.fetchone() is not None

    def remove(self, user_id: Any, post_id: Any) -> int:
        """Delete a like edge; returns the number of rows affected."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM likes WHERE user_id = %s AND post_id = %s",
                (user_id, post_id),
            )
            return cursor.rowcount


class PostMetadataRepository:
    """CRUD for post_metadata table backed by PostgreSQL JSONB."""

    def __init__(self, pg_connection: PostgresConnection):
        self._pg_connection = pg_connection

    def upsert(
        self, post_id: int, tags: list[str] | None = None, location: str | None = None
    ) -> None:
        """Insert metadata for a post or merge it into the existing JSONB row."""
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
        """Return the metadata doc for a post, or None if it has none."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute("SELECT metadata FROM post_metadata WHERE post_id = %s", (post_id,))
            row = cursor.fetchone()
            return row["metadata"] if row else None

    def find_many(self, post_ids: list[int]) -> dict[int, dict]:
        """Return {post_id: metadata} for the given post ids."""
        if not post_ids:
            return {}
        with self._pg_connection.cursor() as cursor:
            cursor.execute(
                "SELECT post_id, metadata FROM post_metadata WHERE post_id = ANY(%s)",
                (post_ids,),
            )
            return {row["post_id"]: row["metadata"] for row in cursor.fetchall()}

    def delete(self, post_id: int) -> None:
        """Remove the metadata row for a post."""
        with self._pg_connection.cursor() as cursor:
            cursor.execute("DELETE FROM post_metadata WHERE post_id = %s", (post_id,))
