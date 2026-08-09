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
    URLNotOwnedError,
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


class TestURLShortenerServiceListOwned:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.service = URLShortenerService(repository=self.repository, generator=self.generator)

    def test_delegates_to_repository(self):
        owner = Mock(id=1)
        expected = [Mock(), Mock()]
        self.repository.list_by_owner.return_value = expected

        assert self.service.list_owned(owner) is expected
        self.repository.list_by_owner.assert_called_once_with(owner)


class TestURLShortenerServiceUpdateOwned:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.service = URLShortenerService(repository=self.repository, generator=self.generator)

    def test_updates_when_owned(self):
        owner = Mock(id=1)
        existing = Mock(owner_id=1)
        updated = Mock()
        self.repository.get_by_id.return_value = existing
        self.repository.update.return_value = updated

        result = self.service.update_owned(
            pk=5, owner=owner, original_url="https://new.example.com"
        )

        assert result is updated
        self.repository.update.assert_called_once_with(
            existing, original_url="https://new.example.com"
        )

    def test_raises_when_missing(self):
        owner = Mock(id=1)
        self.repository.get_by_id.return_value = None

        with pytest.raises(URLNotOwnedError):
            self.service.update_owned(pk=5, owner=owner, original_url="https://new.example.com")

        self.repository.update.assert_not_called()

    def test_raises_when_owned_by_someone_else(self):
        owner = Mock(id=1)
        existing = Mock(owner_id=2)
        self.repository.get_by_id.return_value = existing

        with pytest.raises(URLNotOwnedError):
            self.service.update_owned(pk=5, owner=owner, original_url="https://new.example.com")

        self.repository.update.assert_not_called()


class TestURLShortenerServiceDeleteOwned:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.service = URLShortenerService(repository=self.repository, generator=self.generator)

    def test_deletes_when_owned(self):
        owner = Mock(id=1)
        existing = Mock(owner_id=1)
        self.repository.get_by_id.return_value = existing

        self.service.delete_owned(pk=5, owner=owner)

        self.repository.delete.assert_called_once_with(existing)

    def test_raises_when_missing(self):
        owner = Mock(id=1)
        self.repository.get_by_id.return_value = None

        with pytest.raises(URLNotOwnedError):
            self.service.delete_owned(pk=5, owner=owner)

        self.repository.delete.assert_not_called()

    def test_raises_when_owned_by_someone_else(self):
        owner = Mock(id=1)
        existing = Mock(owner_id=2)
        self.repository.get_by_id.return_value = existing

        with pytest.raises(URLNotOwnedError):
            self.service.delete_owned(pk=5, owner=owner)

        self.repository.delete.assert_not_called()
