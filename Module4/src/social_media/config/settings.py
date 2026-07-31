"""Load and validate configuration from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from social_media.exceptions import SettingsError

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from the environment."""

    mongo_uri: str
    mongo_db_name: str
    mongo_username: str
    mongo_password: str
    mongo_auth_source: str
    pg_host: str
    pg_port: int
    pg_db: str
    pg_user: str
    pg_password: str
    pg_pool_min: int
    pg_pool_max: int
    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str
    bcrypt_rounds: int
    app_secret_key: str
    app_env: str
    log_level: str

    @staticmethod
    def _require(key: str) -> str:
        """Return the env var value or raise SettingsError when missing."""
        value = os.getenv(key)
        if not value:
            raise SettingsError(f"Missing required env var: {key}")
        return value

    @classmethod
    def load(cls) -> "Settings":
        """Load all settings from the environment, applying defaults."""
        return cls(
            mongo_uri=cls._require("MONGO_URI"),
            mongo_db_name=cls._require("MONGO_DB_NAME"),
            mongo_username=os.getenv("MONGO_USERNAME", ""),
            mongo_password=os.getenv("MONGO_PASSWORD", ""),
            mongo_auth_source=os.getenv("MONGO_AUTH_SOURCE", "admin"),
            pg_host=os.getenv("PG_HOST", "localhost"),
            pg_port=int(os.getenv("PG_PORT", "5432")),
            pg_db=os.getenv("PG_DB", "social_media"),
            pg_user=os.getenv("PG_USER", "postgres"),
            pg_password=os.getenv("PG_PASSWORD", ""),
            pg_pool_min=int(os.getenv("PG_POOL_MIN", "1")),
            pg_pool_max=int(os.getenv("PG_POOL_MAX", "10")),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD", ""),
            bcrypt_rounds=int(os.getenv("BCRYPT_ROUNDS", "12")),
            app_secret_key=cls._require("APP_SECRET_KEY"),
            app_env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


settings = Settings.load()
