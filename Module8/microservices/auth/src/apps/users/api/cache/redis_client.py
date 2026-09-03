"""Redis connection management with graceful degradation.

Provides a singleton Redis client used by ``RedisLoginRateLimiter`` —
this service's own copy, distinct from the shortener service's, since
each microservice owns its infrastructure clients independently rather
than importing across service boundaries.

Only wraps the operations the rate limiter actually calls
(``set``/``delete``/``incr``/``ttl``) — this is a purpose-built client
for one job, not a general-purpose Redis library.
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
    """Thread-safe Redis client wrapper with connection pooling."""

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

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        try:
            serialized = json.dumps(value) if not isinstance(value, str) else value
            self._client.set(name=key, value=serialized, ex=ttl or self._DEFAULT_TTL)
            return True
        except (redis.ConnectionError, redis.TimeoutError) as exc:
            logger.warning("redis.set_failed key=%s error=%s", key, exc)
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(self._client.delete(key))
        except (redis.ConnectionError, redis.TimeoutError) as exc:
            logger.warning("redis.delete_failed key=%s error=%s", key, exc)
            return False

    def incr(self, key: str, ttl: int | None = None) -> int:
        """Atomically increment a counter, applying ``ttl`` only when the key is new."""
        try:
            # redis-py types this as the union it also uses for its async
            # client; this instance is always the sync one (no `await`
            # anywhere here), so the runtime value is always a plain int.
            value = cast(int, self._client.incr(key))
            if value == 1 and ttl:
                self._client.expire(key, ttl)
            return value
        except (redis.ConnectionError, redis.TimeoutError) as exc:
            logger.warning("redis.incr_failed key=%s error=%s", key, exc)
            return 0

    def ttl(self, key: str) -> int:
        """Return the remaining TTL in seconds for ``key``, or ``0`` if unset/unreachable."""
        try:
            value = cast(int, self._client.ttl(key))
            return value if value > 0 else 0
        except (redis.ConnectionError, redis.TimeoutError) as exc:
            logger.warning("redis.ttl_failed key=%s error=%s", key, exc)
            return 0

    def ping(self) -> bool:
        """Health check. Returns ``True`` if Redis is reachable."""
        try:
            return cast(bool, self._client.ping())
        except (redis.ConnectionError, redis.TimeoutError):
            return False


def get_redis_client() -> RedisClient:
    """Return the singleton :class:`RedisClient` instance."""
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = RedisClient()
    return _REDIS_CLIENT
