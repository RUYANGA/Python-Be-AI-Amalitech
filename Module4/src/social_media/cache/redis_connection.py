"""Redis connection manager.

Encapsulates client setup and provides a client property for cache ops.
"""

from typing import Optional

import redis

from social_media.config.settings import Settings
from social_media.utils.logger import get_logger

log = get_logger(__name__)

TIMELINE_TTL = 60  # seconds


class RedisConnection:
    """Redis connection wrapper — inject Settings rather than importing globally."""

    _instance: Optional["RedisConnection"] = None

    def __new__(cls, settings: Settings) -> "RedisConnection":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client(settings)
        return cls._instance

    def _init_client(self, settings: Settings) -> None:
        """Create the Redis client and verify connectivity."""
        kwargs = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
            "decode_responses": True,
        }
        if settings.redis_password:
            kwargs["password"] = settings.redis_password

        try:
            self._client: redis.Redis = redis.Redis(**kwargs)
            self._client.ping()
            log.info("Connected to Redis at %s:%s", settings.redis_host, settings.redis_port)
        except Exception as exc:
            log.error("Redis connection failed: %s", exc)
            raise

    @property
    def client(self) -> redis.Redis:
        """The configured Redis client for cache operations."""
        return self._client

    def close(self) -> None:
        """Close the Redis connection."""
        self._client.close()
        log.info("Redis connection closed")
