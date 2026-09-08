"""Redis-backed per-domain circuit breaker.

State lives in Redis, not in-process memory, so it's shared across the
(single) web process — matters once this ever scales to more than one
replica: every replica sees the same open/closed state for a domain.
"""

from __future__ import annotations

import logging

from apps.preview.api.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

_FAIL_COUNTER_TTL_SECONDS = 120


class DomainCircuitBreaker:
    """Tracks fetch failures per domain and short-circuits repeat offenders.

    - ``allow(domain)`` — ``False`` while the circuit is open for that
      domain; Redis' own key TTL handles the "half-open" transition, so
      "not open" just means the open-key has expired or was never set.
    - ``record_failure(domain)`` — increments a sliding failure counter
      (TTL ``120s``); once it reaches ``failure_threshold``, opens the
      circuit for ``open_seconds``.
    - ``record_success(domain)`` — clears both the open-key and the
      failure counter, closing the circuit immediately.
    """

    def __init__(
        self,
        redis_client: RedisClient,
        failure_threshold: int,
        open_seconds: int,
    ) -> None:
        self._redis = redis_client
        self._failure_threshold = failure_threshold
        self._open_seconds = open_seconds

    def allow(self, domain: str) -> bool:
        """Return ``True`` unless the circuit is currently open for ``domain``."""
        return self._redis.get(self._open_key(domain)) is None

    def record_success(self, domain: str) -> None:
        """Close the circuit for ``domain``, clearing any failure history."""
        self._redis.delete(self._open_key(domain))
        self._redis.delete(self._fail_key(domain))

    def record_failure(self, domain: str) -> None:
        """Record a failure for ``domain``, opening the circuit past the threshold."""
        count = self._redis.incr(self._fail_key(domain), ttl=_FAIL_COUNTER_TTL_SECONDS)
        if count >= self._failure_threshold:
            logger.warning(
                "circuit_breaker.opened domain=%s failure_count=%s open_seconds=%s",
                domain,
                count,
                self._open_seconds,
            )
            self._redis.set(self._open_key(domain), "1", ttl=self._open_seconds)

    @staticmethod
    def _open_key(domain: str) -> str:
        return f"preview:circuit:open:{domain}"

    @staticmethod
    def _fail_key(domain: str) -> str:
        return f"preview:circuit:fail:{domain}"
