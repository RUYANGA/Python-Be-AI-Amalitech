"""Unit tests for :class:`URLShortenerService`.

The service depends on interfaces, so these tests use ``unittest.mock``
doubles instead of the database. No ``pytest.mark.django_db`` needed.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from apps.shortener.api.exceptions import (
    ShortCodeGenerationError,
    URLNotFoundError,
)
from apps.shortener.api.services.url_service import URLShortenerService


class TestURLShortenerServiceShorten:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.service = URLShortenerService(repository=self.repository, generator=self.generator)

    def test_generates_and_persists(self):
        self.generator.generate.return_value = "abc1234"
        self.repository.exists_by_short_code.return_value = False
        expected = Mock()
        self.repository.create.return_value = expected

        result = self.service.shorten("https://example.com")

        assert result is expected
        self.repository.create.assert_called_once_with(
            original_url="https://example.com",
            short_code="abc1234",
            owner=None,
        )

    def test_retries_on_short_code_collision(self):
        self.generator.generate.side_effect = ["taken1", "free01"]
        self.repository.exists_by_short_code.side_effect = [True, False]
        self.repository.create.return_value = Mock()

        self.service.shorten("https://example.com")

        assert self.generator.generate.call_count == 2
        _, kwargs = self.repository.create.call_args
        assert kwargs["short_code"] == "free01"

    def test_raises_after_exhausting_attempts(self):
        self.generator.generate.return_value = "taken1"
        self.repository.exists_by_short_code.return_value = True

        with pytest.raises(ShortCodeGenerationError):
            self.service.shorten("https://example.com")

        assert self.generator.generate.call_count == URLShortenerService.MAX_GENERATION_ATTEMPTS
        self.repository.create.assert_not_called()

    def test_passes_owner_to_repository(self):
        owner = Mock(id=42)
        self.generator.generate.return_value = "own1234"
        self.repository.exists_by_short_code.return_value = False
        self.repository.create.return_value = Mock()

        self.service.shorten("https://example.com", owner=owner)

        _, kwargs = self.repository.create.call_args
        assert kwargs["owner"] is owner


class TestURLShortenerServiceCreate:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.service = URLShortenerService(repository=self.repository, generator=self.generator)

    def test_create_applies_optional_fields_via_update(self):
        self.generator.generate.return_value = "abc1234"
        self.repository.exists_by_short_code.return_value = False
        created = Mock()
        self.repository.create.return_value = created
        updated = Mock()
        self.service.update = Mock(return_value=updated)

        result = self.service.create(
            "https://example.com",
            title="landing",
            tags=["marketing"],
            expires_at="2026-12-31T00:00:00Z",
        )

        assert result is updated
        self.service.update.assert_called_once_with(
            created,
            title="landing",
            tags=["marketing"],
            expires_at="2026-12-31T00:00:00Z",
        )

    def test_create_skips_update_when_no_optional_fields(self):
        self.generator.generate.return_value = "abc1234"
        self.repository.exists_by_short_code.return_value = False
        created = Mock()
        self.repository.create.return_value = created
        self.service.update = Mock()

        result = self.service.create("https://example.com")

        assert result is created
        self.service.update.assert_not_called()


class TestURLShortenerServiceResolve:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.service = URLShortenerService(repository=self.repository, generator=self.generator)

    def test_returns_url_when_found(self):
        expected = Mock()
        self.repository.get_by_short_code.return_value = expected

        assert self.service.resolve("abc1234") is expected
        self.repository.get_by_short_code.assert_called_once_with("abc1234")

    def test_raises_when_not_found(self):
        self.repository.get_by_short_code.return_value = None

        with pytest.raises(URLNotFoundError) as excinfo:
            self.service.resolve("missing")

        assert excinfo.value.short_code == "missing"
