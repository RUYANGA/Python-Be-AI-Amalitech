"""Concrete PostgreSQL repositories, one per table, mirroring the 3NF schema.

PostgresRepository/PostgresCompositeRepository play the same shared-CRUD
role MongoRepository plays for the Mongo repos — generic parameterized
insert/find_by_id/find/update/delete, with each concrete class adding only
its own query methods.
"""

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

    def __init__(self, pg: PostgresConnection):
        self._pg = pg

    def insert(self, document: dict) -> Any:
        cols = list(document.keys())
        placeholders = ", ".join(["%s"] * len(cols))
        col_sql = ", ".join(cols)
        sql = (
            f"INSERT INTO {self.TABLE} ({col_sql}) VALUES ({placeholders}) "
            f"RETURNING {self.ID_COLUMN}"
        )
        with self._pg.cursor() as cur:
            cur.execute(sql, list(document.values()))
            return cur.fetchone()[self.ID_COLUMN]

    def find_by_id(self, _id: Any) -> dict | None:
        with self._pg.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {self.TABLE} WHERE {self.ID_COLUMN} = %s", (_id,)
            )
            return cur.fetchone()

    def find(self, query: dict, limit: int = 0) -> list[dict]:
        where_sql, params = "", []
        if query:
            where_sql = "WHERE " + " AND ".join(f"{col} = %s" for col in query)
            params = list(query.values())
        limit_sql = f" LIMIT {int(limit)}" if limit else ""
        sql = f"SELECT * FROM {self.TABLE} {where_sql} ORDER BY {self.ID_COLUMN}{limit_sql}"
        with self._pg.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def update(self, _id: Any, changes: dict) -> int:
        set_sql = ", ".join(f"{col} = %s" for col in changes)
        sql = f"UPDATE {self.TABLE} SET {set_sql} WHERE {self.ID_COLUMN} = %s"
        with self._pg.cursor() as cur:
            cur.execute(sql, [*changes.values(), _id])
            return cur.rowcount

    def delete(self, _id: Any) -> int:
        with self._pg.cursor() as cur:
            cur.execute(f"DELETE FROM {self.TABLE} WHERE {self.ID_COLUMN} = %s", (_id,))
            return cur.rowcount


class PostgresCompositeRepository(IRepository):
    """Shared CRUD for tables keyed by a (col_a, col_b) composite PK."""

    TABLE: str = ""
    KEY_COLUMNS: tuple[str, str] = ("", "")

    def __init__(self, pg: PostgresConnection):
        self._pg = pg

    def _key_where(self) -> str:
        a, b = self.KEY_COLUMNS
        return f"{a} = %s AND {b} = %s"

    def insert(self, document: dict) -> Any:
        cols = list(document.keys())
        placeholders = ", ".join(["%s"] * len(cols))
        col_sql = ", ".join(cols)
        sql = f"INSERT INTO {self.TABLE} ({col_sql}) VALUES ({placeholders})"
        with self._pg.cursor() as cur:
            cur.execute(sql, list(document.values()))
        a, b = self.KEY_COLUMNS
        return (document[a], document[b])

    def find_by_id(self, _id: tuple) -> dict | None:
        with self._pg.cursor() as cur:
            cur.execute(f"SELECT * FROM {self.TABLE} WHERE {self._key_where()}", _id)
            return cur.fetchone()

    def find(self, query: dict, limit: int = 0) -> list[dict]:
        where_sql, params = "", []
        if query:
            where_sql = "WHERE " + " AND ".join(f"{col} = %s" for col in query)
            params = list(query.values())
        limit_sql = f" LIMIT {int(limit)}" if limit else ""
        sql = f"SELECT * FROM {self.TABLE} {where_sql} ORDER BY created_at{limit_sql}"
        with self._pg.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def update(self, _id: tuple, changes: dict) -> int:
        set_sql = ", ".join(f"{col} = %s" for col in changes)
        sql = f"UPDATE {self.TABLE} SET {set_sql} WHERE {self._key_where()}"
        with self._pg.cursor() as cur:
            cur.execute(sql, [*changes.values(), *_id])
            return cur.rowcount

    def delete(self, _id: tuple) -> int:
        with self._pg.cursor() as cur:
            cur.execute(f"DELETE FROM {self.TABLE} WHERE {self._key_where()}", _id)
            return cur.rowcount


class UserRepository(PostgresRepository, IUserRepository):
    TABLE = "users"

    def find_by_email(self, email: str) -> dict | None:
        with self._pg.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cur.fetchone()


class PostRepository(PostgresRepository, IPostRepository):
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

    def feed_for_user_ids(
        self, user_ids: list[Any], limit: int = 20, offset: int = 0
    ) -> list:
        with self._pg.cursor() as cur:
            cur.execute(self.FEED_QUERY, (user_ids, offset, offset + limit))
            return cur.fetchall()

    def trending(self, limit: int = 20, since_hours: int = 168) -> list:
        with self._pg.cursor() as cur:
            cur.execute(self.TRENDING_QUERY, (since_hours, limit))
            return cur.fetchall()

    def increment_like_count(self, post_id: Any, delta: int) -> None:
        with self._pg.cursor() as cur:
            cur.execute(
                "UPDATE posts SET like_count = like_count + %s WHERE id = %s",
                (delta, post_id),
            )

    def increment_comment_count(self, post_id: Any, delta: int) -> None:
        with self._pg.cursor() as cur:
            cur.execute(
                "UPDATE posts SET comment_count = comment_count + %s WHERE id = %s",
                (delta, post_id),
            )


class CommentRepository(PostgresRepository, ICommentRepository):
    TABLE = "comments"

    def for_post(self, post_id: Any) -> list:
        with self._pg.cursor() as cur:
            cur.execute(
                "SELECT * FROM comments WHERE post_id = %s AND NOT is_deleted "
                "ORDER BY created_at ASC",
                (post_id,),
            )
            return cur.fetchall()


class FollowerRepository(PostgresCompositeRepository, IFollowerRepository):
    TABLE = "followers"
    KEY_COLUMNS = ("follower_id", "followee_id")

    def follow(self, follower_id: Any, followee_id: Any) -> bool:
        """Insert the edge and bump both counters atomically. False on duplicate."""
        try:
            with self._pg.cursor() as cur:
                cur.execute(
                    "INSERT INTO followers (follower_id, followee_id) VALUES (%s, %s)",
                    (follower_id, followee_id),
                )
                cur.execute(
                    "UPDATE users SET following_count = following_count + 1 WHERE id = %s",
                    (follower_id,),
                )
                cur.execute(
                    "UPDATE users SET follower_count = follower_count + 1 WHERE id = %s",
                    (followee_id,),
                )
            return True
        except psycopg2.errors.UniqueViolation:
            return False

    def unfollow(self, follower_id: Any, followee_id: Any) -> int:
        with self._pg.cursor() as cur:
            cur.execute(
                "DELETE FROM followers WHERE follower_id = %s AND followee_id = %s",
                (follower_id, followee_id),
            )
            deleted = cur.rowcount
            if deleted:
                cur.execute(
                    "UPDATE users SET following_count = GREATEST(following_count - 1, 0) "
                    "WHERE id = %s",
                    (follower_id,),
                )
                cur.execute(
                    "UPDATE users SET follower_count = GREATEST(follower_count - 1, 0) "
                    "WHERE id = %s",
                    (followee_id,),
                )
            return deleted

    def followees_of(self, user_id: Any) -> list[Any]:
        with self._pg.cursor() as cur:
            cur.execute(
                "SELECT followee_id FROM followers WHERE follower_id = %s", (user_id,)
            )
            return [row["followee_id"] for row in cur.fetchall()]

    def followers_of(self, user_id: Any) -> list[Any]:
        with self._pg.cursor() as cur:
            cur.execute(
                "SELECT follower_id FROM followers WHERE followee_id = %s", (user_id,)
            )
            return [row["follower_id"] for row in cur.fetchall()]


class LikeRepository(PostgresCompositeRepository, ILikeRepository):
    TABLE = "likes"
    KEY_COLUMNS = ("user_id", "post_id")

    def exists(self, user_id: Any, post_id: Any) -> bool:
        with self._pg.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM likes WHERE user_id = %s AND post_id = %s",
                (user_id, post_id),
            )
            return cur.fetchone() is not None

    def remove(self, user_id: Any, post_id: Any) -> int:
        with self._pg.cursor() as cur:
            cur.execute(
                "DELETE FROM likes WHERE user_id = %s AND post_id = %s",
                (user_id, post_id),
            )
            return cur.rowcount
