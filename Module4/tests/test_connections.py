"""Tests for Redis/MongoDB/PostgreSQL connection managers and composition root."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pymongo.errors import ConnectionFailure

from social_media.cache.redis_connection import RedisConnection
from social_media.composition import build_services
from social_media.config.settings import Settings
from social_media.database.mongodb_connection import MongoConnection
from social_media.database.postgres_connection import PostgresConnection


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = dict(
        mongo_uri="mongodb://localhost:27017",
        mongo_db_name="social",
        mongo_username="",
        mongo_password="",
        mongo_auth_source="admin",
        pg_host="localhost",
        pg_port=5432,
        pg_db="social",
        pg_user="postgres",
        pg_password="",
        pg_pool_min=1,
        pg_pool_max=10,
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password="",
        bcrypt_rounds=12,
        app_secret_key="secret",
        app_env="test",
        log_level="INFO",
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture(autouse=True)
def _reset_singletons():
    RedisConnection._instance = None
    MongoConnection._instance = None
    PostgresConnection._instance = None
    yield
    RedisConnection._instance = None
    MongoConnection._instance = None
    PostgresConnection._instance = None


# ── RedisConnection ──────────────────────────────────────────────────


class TestRedisConnection:
    @patch("social_media.cache.redis_connection.redis.Redis")
    def test_creates_client_and_pings(self, mock_redis_cls):
        client = MagicMock()
        mock_redis_cls.return_value = client

        conn = RedisConnection(make_settings())

        mock_redis_cls.assert_called_once_with(
            host="localhost", port=6379, db=0, decode_responses=True
        )
        client.ping.assert_called_once()
        assert conn.client is client

    @patch("social_media.cache.redis_connection.redis.Redis")
    def test_includes_password_when_set(self, mock_redis_cls):
        client = MagicMock()
        mock_redis_cls.return_value = client

        RedisConnection(make_settings(redis_password="secret"))

        assert mock_redis_cls.call_args[1]["password"] == "secret"

    @patch("social_media.cache.redis_connection.redis.Redis")
    def test_raises_when_ping_fails(self, mock_redis_cls):
        client = MagicMock()
        client.ping.side_effect = ConnectionError("down")
        mock_redis_cls.return_value = client

        with pytest.raises(ConnectionError, match="down"):
            RedisConnection(make_settings())

    @patch("social_media.cache.redis_connection.redis.Redis")
    def test_singleton_reuses_instance(self, mock_redis_cls):
        client = MagicMock()
        mock_redis_cls.return_value = client

        first = RedisConnection(make_settings())
        second = RedisConnection(make_settings())

        assert first is second
        mock_redis_cls.assert_called_once()

    @patch("social_media.cache.redis_connection.redis.Redis")
    def test_close(self, mock_redis_cls):
        client = MagicMock()
        mock_redis_cls.return_value = client

        conn = RedisConnection(make_settings())
        conn.close()

        client.close.assert_called_once()


# ── MongoConnection ──────────────────────────────────────────────────


class TestMongoConnection:
    @patch("social_media.database.mongodb_connection.MongoClient")
    def test_init_without_credentials(self, mock_client_cls):
        client = MagicMock()
        client.admin.command.return_value = {"ok": 1}
        client.list_database_names.return_value = ["social"]
        mock_client_cls.return_value = client

        conn = MongoConnection(make_settings())

        mock_client_cls.assert_called_once_with(
            host="mongodb://localhost:27017", serverSelectionTimeoutMS=5000
        )
        client.admin.command.assert_called_once_with("ping")
        assert conn.db is client["social"]

    @patch("social_media.database.mongodb_connection.MongoClient")
    def test_init_with_credentials(self, mock_client_cls):
        client = MagicMock()
        client.admin.command.return_value = {"ok": 1}
        mock_client_cls.return_value = client

        MongoConnection(make_settings(mongo_username="u", mongo_password="p"))

        kwargs = mock_client_cls.call_args[1]
        assert kwargs["username"] == "u"
        assert kwargs["password"] == "p"
        assert kwargs["authSource"] == "admin"

    @patch("social_media.database.mongodb_connection.MongoClient")
    def test_ping_failure_raises(self, mock_client_cls):
        client = MagicMock()
        client.admin.command.side_effect = ConnectionFailure("down")
        mock_client_cls.return_value = client

        with pytest.raises(ConnectionFailure, match="down"):
            MongoConnection(make_settings())

    @patch("social_media.database.mongodb_connection.MongoClient")
    def test_resolves_case_insensitive_db_name(self, mock_client_cls):
        client = MagicMock()
        client.admin.command.return_value = {"ok": 1}
        client.list_database_names.return_value = ["School"]
        mock_client_cls.return_value = client

        conn = MongoConnection(make_settings(mongo_db_name="school"))

        assert conn.db is client["School"]

    @patch("social_media.database.mongodb_connection.MongoClient")
    def test_keeps_desired_db_when_no_conflict(self, mock_client_cls):
        client = MagicMock()
        client.admin.command.return_value = {"ok": 1}
        client.list_database_names.return_value = ["other"]
        mock_client_cls.return_value = client

        conn = MongoConnection(make_settings(mongo_db_name="social"))

        assert conn.db is client["social"]

    @patch("social_media.database.mongodb_connection.MongoClient")
    def test_keeps_desired_db_when_exact_match(self, mock_client_cls):
        client = MagicMock()
        client.admin.command.return_value = {"ok": 1}
        client.list_database_names.return_value = ["social"]
        mock_client_cls.return_value = client

        conn = MongoConnection(make_settings(mongo_db_name="social"))

        assert conn.db is client["social"]

    @patch("social_media.database.mongodb_connection.MongoClient")
    def test_close(self, mock_client_cls):
        client = MagicMock()
        client.admin.command.return_value = {"ok": 1}
        mock_client_cls.return_value = client

        conn = MongoConnection(make_settings())
        conn.close()

        client.close.assert_called_once()


# ── PostgresConnection ───────────────────────────────────────────────


class TestPostgresConnection:
    def test_pool_init_failure_raises(self):
        with (
            patch(
                "social_media.database.postgres_connection.ThreadedConnectionPool",
                side_effect=Exception("pg down"),
            ),
            pytest.raises(Exception, match="pg down"),
        ):
            PostgresConnection(make_settings())

    def test_successful_init_and_close(self):
        pool = MagicMock()
        conn_obj = MagicMock()
        cur = MagicMock()
        conn_obj.cursor.return_value.__enter__.return_value = cur
        conn_obj.cursor.return_value.__exit__.return_value = False
        pool.getconn.return_value = conn_obj

        with patch(
            "social_media.database.postgres_connection.ThreadedConnectionPool",
            return_value=pool,
        ):
            conn = PostgresConnection(make_settings())
            conn.close()

        pool.closeall.assert_called_once()
        cur.execute.assert_called_once()
        conn_obj.commit.assert_called_once()

    def test_cursor_rolls_back_on_error(self):
        pool = MagicMock()
        conn_obj = MagicMock()
        conn_obj.cursor.return_value.__enter__.return_value = MagicMock()
        conn_obj.cursor.return_value.__exit__.return_value = False
        pool.getconn.return_value = conn_obj

        with patch(
            "social_media.database.postgres_connection.ThreadedConnectionPool",
            return_value=pool,
        ):
            conn = PostgresConnection(make_settings())
            with pytest.raises(RuntimeError), conn.cursor() as cur:
                cur.execute("SELECT boom")
                raise RuntimeError("boom")
            conn_obj.rollback.assert_called_once()
            assert pool.putconn.call_count == 2


# ── build_services ───────────────────────────────────────────────────


class TestBuildServices:
    @patch("social_media.composition.PasswordValidator")
    @patch("social_media.composition.PasswordHasher")
    @patch("social_media.composition.RedisConnection")
    @patch("social_media.composition.ActivityLogService")
    @patch("social_media.composition.ActivityLogRepository")
    @patch("social_media.composition.MongoConnection")
    @patch("social_media.composition.PostMetadataRepository")
    @patch("social_media.composition.LikeRepository")
    @patch("social_media.composition.FollowerRepository")
    @patch("social_media.composition.CommentRepository")
    @patch("social_media.composition.PostRepository")
    @patch("social_media.composition.UserRepository")
    @patch("social_media.composition.PostgresConnection")
    def test_build_services_wires_all_dependencies(
        self,
        mock_pg,
        mock_user_repo,
        mock_post_repo,
        mock_comment_repo,
        mock_follower_repo,
        mock_like_repo,
        mock_metadata_repo,
        mock_mongo,
        mock_activity_repo,
        mock_activity_svc,
        mock_redis,
        mock_hasher,
        mock_validator,
    ):
        svc = build_services()

        assert set(svc) == {"users", "posts", "likes", "comments", "follows", "metadata_repo"}
        assert svc["metadata_repo"] is mock_metadata_repo.return_value
        mock_pg.assert_called_once()
