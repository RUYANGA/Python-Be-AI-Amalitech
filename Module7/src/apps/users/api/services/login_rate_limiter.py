"""Redis-backed rate limiter for the login endpoint.

Blocks a username for ``BLOCK_SECONDS`` once it accrues ``MAX_ATTEMPTS``
failed logins within ``WINDOW_SECONDS``, mitigating brute-force and
credential-stuffing attempts against a single account.
"""

from __future__ import annotations

import logging

from apps.shortener.api.cache.redis_client import RedisClient, get_redis_client
from apps.users.api.exceptions.too_many_login_attempts_error import TooManyLoginAttemptsError
from apps.users.api.interfaces.rate_limiter import LoginRateLimiter

logger = logging.getLogger(__name__)


class RedisLoginRateLimiter(LoginRateLimiter):
    """Fixed-window failed-attempt counter with a temporary block on overflow."""

    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 60
    BLOCK_SECONDS = 30 * 60

    def __init__(self, redis_client: RedisClient | None = None):
        self._cache = redis_client or get_redis_client()

    def check(self, identifier: str) -> None:
        if self._cache.exists(self._blocked_key(identifier)):
            logger.warning("auth.login_blocked identifier=%s", identifier)
            raise TooManyLoginAttemptsError(self.BLOCK_SECONDS)

    def register_failure(self, identifier: str) -> int:
        attempts = self._cache.incr(self._attempts_key(identifier), ttl=self.WINDOW_SECONDS)
        if attempts >= self.MAX_ATTEMPTS:
            self._cache.set(self._blocked_key(identifier), True, ttl=self.BLOCK_SECONDS)
            self._cache.delete(self._attempts_key(identifier))
            logger.warning(
                "auth.login_rate_limited identifier=%s attempts=%s", identifier, attempts
            )
            return 0
        return self.MAX_ATTEMPTS - attempts

    def reset(self, identifier: str) -> None:
        self._cache.delete(self._attempts_key(identifier))

    @staticmethod
    def _attempts_key(identifier: str) -> str:
        return f"auth:login_attempts:{identifier}"

    @staticmethod
    def _blocked_key(identifier: str) -> str:
        return f"auth:login_blocked:{identifier}"
