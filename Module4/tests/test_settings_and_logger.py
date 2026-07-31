"""Tests for Settings loading and the central logger."""

import os
from unittest.mock import patch

import pytest

from social_media.config.settings import Settings
from social_media.exceptions import SettingsError
from social_media.utils.logger import get_logger


class TestSettings:
    def test_require_returns_value(self):
        with patch.dict(os.environ, {"TEST_SETTINGS_KEY": "present"}, clear=False):
            assert Settings._require("TEST_SETTINGS_KEY") == "present"

    def test_require_missing_raises(self):
        with (
            patch.dict(os.environ, {}, clear=False),
            pytest.raises(SettingsError, match="TEST_SETTINGS_KEY"),
        ):
            Settings._require("TEST_SETTINGS_KEY")

    def test_load_uses_defaults(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(
                os.environ,
                {"MONGO_URI": "mongodb://x", "MONGO_DB_NAME": "db", "APP_SECRET_KEY": "k"},
            ),
        ):
            s = Settings.load()
        assert s.pg_host == "localhost"
        assert s.pg_port == 5432
        assert s.mongo_auth_source == "admin"
        assert s.app_env == "development"
        assert s.log_level == "INFO"

    def test_load_requires_uri(self):
        with (
            patch.dict(os.environ, {"MONGO_DB_NAME": "db", "APP_SECRET_KEY": "k"}, clear=True),
            pytest.raises(SettingsError, match="MONGO_URI"),
        ):
            Settings.load()

    def test_load_requires_secret(self):
        with (
            patch.dict(os.environ, {"MONGO_URI": "mongodb://x", "MONGO_DB_NAME": "db"}, clear=True),
            pytest.raises(SettingsError, match="APP_SECRET_KEY"),
        ):
            Settings.load()

    def test_load_parses_ints(self):
        with patch.dict(
            os.environ,
            {
                "MONGO_URI": "mongodb://x",
                "MONGO_DB_NAME": "db",
                "APP_SECRET_KEY": "k",
                "PG_PORT": "5433",
                "REDIS_DB": "2",
                "BCRYPT_ROUNDS": "10",
                "PG_POOL_MIN": "2",
                "PG_POOL_MAX": "5",
            },
            clear=True,
        ):
            s = Settings.load()
        assert s.pg_port == 5433
        assert s.redis_db == 2
        assert s.bcrypt_rounds == 10
        assert s.pg_pool_min == 2
        assert s.pg_pool_max == 5


class TestLogger:
    def test_reuses_logger_with_handlers(self):
        first = get_logger("social_media.utils.logger")
        second = get_logger("social_media.utils.logger")
        assert first is second
        assert first.handlers
