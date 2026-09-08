"""Unit tests for ``PreviewService``.

``IPreviewFetcher`` is a ``Mock(spec=...)`` double throughout — this is
the orchestration layer, so the actual HTTP/HTML work
(``HTMLPreviewFetcher``) is exactly what should stay out of these tests.
The circuit breaker and cache use the real Redis-backed implementations
(see ``conftest.py``'s autouse flush fixture) except where a test needs
to force a specific breaker decision, in which case it's mocked too.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from apps.preview.api.cache.redis_client import get_redis_client
from apps.preview.api.exceptions import (
    CircuitOpenError,
    InvalidURLError,
    PreviewFetchError,
    URLNotAccessibleError,
)
from apps.preview.api.interfaces.fetcher import IPreviewFetcher, PreviewResult
from apps.preview.api.services.circuit_breaker import DomainCircuitBreaker
from apps.preview.api.services.preview_service import PreviewService

_RESULT = PreviewResult(
    title="Example",
    description="An example.",
    favicon_url="https://example.com/favicon.ico",
)


def _default_breaker() -> DomainCircuitBreaker:
    return DomainCircuitBreaker(
        redis_client=get_redis_client(), failure_threshold=5, open_seconds=60
    )


def _service(fetcher, *, breaker=None, max_attempts: int = 3) -> PreviewService:
    return PreviewService(
        fetcher=fetcher,
        breaker=breaker or _default_breaker(),
        cache=get_redis_client(),
        max_attempts=max_attempts,
        base_delay=0.001,
        cache_ttl=600,
    )


class TestFetch:
    def test_retries_then_succeeds(self):
        fetcher = Mock(spec=IPreviewFetcher)
        fetcher.fetch.side_effect = [PreviewFetchError("boom"), _RESULT]
        service = _service(fetcher, max_attempts=3)

        result = service.fetch("https://example.com/")

        assert result == _RESULT
        assert fetcher.fetch.call_count == 2

    def test_raises_url_not_accessible_when_retries_are_exhausted(self):
        fetcher = Mock(spec=IPreviewFetcher)
        fetcher.fetch.side_effect = PreviewFetchError("boom")
        breaker = Mock(spec=DomainCircuitBreaker)
        breaker.allow.return_value = True
        service = _service(fetcher, breaker=breaker, max_attempts=2)

        with pytest.raises(URLNotAccessibleError):
            service.fetch("https://example.com/")

        assert fetcher.fetch.call_count == 2
        breaker.record_failure.assert_called_once_with("example.com")

    def test_short_circuits_without_a_network_call_when_the_circuit_is_open(self):
        fetcher = Mock(spec=IPreviewFetcher)
        breaker = Mock(spec=DomainCircuitBreaker)
        breaker.allow.return_value = False
        service = _service(fetcher, breaker=breaker)

        with pytest.raises(CircuitOpenError) as exc_info:
            service.fetch("https://example.com/")

        assert exc_info.value.domain == "example.com"
        fetcher.fetch.assert_not_called()

    def test_ssrf_guard_rejects_a_loopback_target(self):
        fetcher = Mock(spec=IPreviewFetcher)
        service = _service(fetcher)

        with pytest.raises(InvalidURLError):
            service.fetch("http://127.0.0.1/")

        fetcher.fetch.assert_not_called()

    def test_ssrf_guard_rejects_a_link_local_metadata_target(self):
        fetcher = Mock(spec=IPreviewFetcher)
        service = _service(fetcher)

        with pytest.raises(InvalidURLError):
            service.fetch("http://169.254.169.254/")

        fetcher.fetch.assert_not_called()

    def test_rejects_a_disallowed_scheme(self):
        fetcher = Mock(spec=IPreviewFetcher)
        service = _service(fetcher)

        with pytest.raises(InvalidURLError):
            service.fetch("ftp://example.com/")

        fetcher.fetch.assert_not_called()

    def test_successful_fetch_is_cached_and_the_fetcher_is_not_called_again(self):
        fetcher = Mock(spec=IPreviewFetcher)
        fetcher.fetch.return_value = _RESULT
        service = _service(fetcher)

        first = service.fetch("https://example.com/")
        second = service.fetch("https://example.com/")

        assert first == _RESULT
        assert second == _RESULT
        fetcher.fetch.assert_called_once()
