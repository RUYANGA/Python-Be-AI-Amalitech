"""Redis-backed caching utilities for the analytics app."""

from apps.analytics.api.cache.redis_client import RedisClient, get_redis_client

__all__ = ["RedisClient", "get_redis_client"]
