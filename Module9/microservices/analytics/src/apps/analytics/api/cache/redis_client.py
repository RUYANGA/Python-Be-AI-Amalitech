"""Redis connection management with automatic reconnection and health checks.

Provides a singleton Redis client that handles connection pooling,
serialization, and graceful degradation when Redis is unavailable. This
backs the analytics read cache only (``CachedClickAnalyticsRepository``)
— so this only wraps the operations the cache actually calls.
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

_REDIS_CLIENT: RedisClient | None = None


class RedisClient:
    """Thread-safe Redis client wrapper with connection pooling.

    Features:
        - Automatic connection pooling via ``redis.ConnectionPool``
        - JSON serialization/deserialization for complex data types
        - Graceful degradation: returns ``None`` on connection failures
        - Configurable TTL (time-to-live) for cached entries
        - Health check endpoint for monitoring
    """

    _DEFAULT_TTL: int = 300  # 5 minutes

    def __init__(
        self,
        url: str | None = None,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ) -> None:
        self._url: str = str(url or getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0"))
        self._pool = redis.ConnectionPool.from_url(
            self._url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Retrieve a value by key. Returns ``None`` on miss or error."""
        try:
            # redis-py types this as the union it also uses for its async
            # client; this instance is always the sync one (no `await`
            # anywhere here), so the runtime value is always str or None.
            raw = cast("str | None", self._client.get(key))
            if raw is None:
                return None
            return json.loads(raw)
        except (redis.ConnectionError, redis.TimeoutError) as exc:
            logger.warning("redis.get_failed key=%s error=%s", key, exc)
            return None
        except json.JSONDecodeError:
            return raw

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Store a value with optional TTL. Returns ``True`` on success."""
        try:
            serialized = json.dumps(value) if not isinstance(value, str) else value
            self._client.set(
                name=key,
                value=serialized,
                ex=ttl or self._DEFAULT_TTL,
            )
            return True
        except (redis.ConnectionError, redis.TimeoutError) as exc:
            logger.warning("redis.set_failed key=%s error=%s", key, exc)
            return False

    def delete(self, key: str) -> bool:
        """Remove a key. Returns ``True`` if the key existed."""
        try:
            return bool(self._client.delete(key))
        except (redis.ConnectionError, redis.TimeoutError) as exc:
            logger.warning("redis.delete_failed key=%s error=%s", key, exc)
            return False

    def ping(self) -> bool:
        """Health check. Returns ``True`` if Redis is reachable."""
        try:
            return cast(bool, self._client.ping())
        except (redis.ConnectionError, redis.TimeoutError):
            return False

    def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern. Returns count removed."""
        try:
            keys = list(self._client.scan_iter(match=pattern, count=100))
            if keys:
                return cast(int, self._client.delete(*keys))
            return 0
        except (redis.ConnectionError, redis.TimeoutError) as exc:
            logger.warning("redis.flush_pattern_failed pattern=%s error=%s", pattern, exc)
            return 0


def get_redis_client() -> RedisClient:
    """Return the singleton :class:`RedisClient` instance.

    Lazily initialised on first call using settings from ``settings.py``.
    """
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = RedisClient()
    return _REDIS_CLIENT
