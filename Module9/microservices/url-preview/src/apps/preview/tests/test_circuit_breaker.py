"""Unit tests for ``DomainCircuitBreaker``.

Runs against a real Redis (see ``conftest.py``'s autouse ``preview:*``
flush fixture — this test environment assumes a real Redis is reachable
at ``REDIS_URL``, same as ``shortener``'s own tests assume for
``CachedURLRepository``, see ``_clear_url_cache`` there) rather than
mocking ``RedisClient`` — the interesting behaviour here (TTL-driven
"half-open" recovery, the sliding failure window) is exactly what a
mock would paper over.
"""

from __future__ import annotations

from apps.preview.api.cache.redis_client import get_redis_client
from apps.preview.api.services.circuit_breaker import DomainCircuitBreaker

_THRESHOLD = 3


def _breaker() -> DomainCircuitBreaker:
    return DomainCircuitBreaker(
        redis_client=get_redis_client(),
        failure_threshold=_THRESHOLD,
        open_seconds=60,
    )


class TestAllow:
    def test_allows_a_domain_with_no_recorded_failures(self):
        breaker = _breaker()

        assert breaker.allow("example.com") is True

    def test_opens_after_reaching_the_failure_threshold(self):
        breaker = _breaker()

        for _ in range(_THRESHOLD):
            breaker.record_failure("flaky.example.com")

        assert breaker.allow("flaky.example.com") is False

    def test_stays_closed_below_the_failure_threshold(self):
        breaker = _breaker()

        for _ in range(_THRESHOLD - 1):
            breaker.record_failure("mostly-fine.example.com")

        assert breaker.allow("mostly-fine.example.com") is True

    def test_does_not_affect_other_domains(self):
        breaker = _breaker()

        for _ in range(_THRESHOLD):
            breaker.record_failure("flaky.example.com")

        assert breaker.allow("unrelated.example.com") is True


class TestRecordSuccess:
    def test_closes_an_open_circuit(self):
        breaker = _breaker()
        for _ in range(_THRESHOLD):
            breaker.record_failure("flaky.example.com")
        assert breaker.allow("flaky.example.com") is False

        breaker.record_success("flaky.example.com")

        assert breaker.allow("flaky.example.com") is True

    def test_clears_the_failure_counter_so_it_takes_a_fresh_threshold_to_reopen(self):
        breaker = _breaker()
        for _ in range(_THRESHOLD - 1):
            breaker.record_failure("recovering.example.com")

        breaker.record_success("recovering.example.com")
        breaker.record_failure("recovering.example.com")

        assert breaker.allow("recovering.example.com") is True
