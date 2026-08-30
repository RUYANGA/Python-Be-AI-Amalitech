"""Unit tests for :class:`URLShortenerService`.

The service depends on interfaces, so these tests use ``unittest.mock``
doubles instead of the database. No ``pytest.mark.django_db`` needed.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from apps.shortener.api.exceptions import (
    CustomAliasNotAllowedError,
    CustomAliasTakenError,
    ShortCodeGenerationError,
    URLLimitExceededError,
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

    def test_blocks_a_free_user_at_the_active_url_limit(self):
        owner = Mock(id=1, is_premium_tier=False)
        self.repository.count_active_by_owner.return_value = (
            URLShortenerService.FREE_TIER_MAX_ACTIVE_URLS
        )

        with pytest.raises(URLLimitExceededError) as exc_info:
            self.service.create("https://example.com", owner=owner)

        assert exc_info.value.limit == URLShortenerService.FREE_TIER_MAX_ACTIVE_URLS
        self.repository.create.assert_not_called()

    def test_allows_a_free_user_below_the_active_url_limit(self):
        owner = Mock(id=1, is_premium_tier=False)
        self.repository.count_active_by_owner.return_value = (
            URLShortenerService.FREE_TIER_MAX_ACTIVE_URLS - 1
        )
        self.generator.generate.return_value = "abc1234"
        self.repository.exists_by_short_code.return_value = False
        created = Mock()
        self.repository.create.return_value = created

        result = self.service.create("https://example.com", owner=owner)

        assert result is created

    def test_premium_users_are_never_limited(self):
        owner = Mock(id=1, is_premium_tier=True)
        self.generator.generate.return_value = "abc1234"
        self.repository.exists_by_short_code.return_value = False
        created = Mock()
        self.repository.create.return_value = created

        result = self.service.create("https://example.com", owner=owner)

        assert result is created
        self.repository.count_active_by_owner.assert_not_called()

    def test_anonymous_owner_is_not_limited(self):
        self.generator.generate.return_value = "abc1234"
        self.repository.exists_by_short_code.return_value = False
        created = Mock()
        self.repository.create.return_value = created

        result = self.service.create("https://example.com")

        assert result is created
        self.repository.count_active_by_owner.assert_not_called()

    def test_premium_user_can_use_a_custom_alias(self):
        owner = Mock(id=1, is_premium_tier=True)
        self.repository.exists_by_short_code.return_value = False
        created = Mock()
        self.repository.create.return_value = created

        result = self.service.create("https://example.com", owner=owner, custom_alias="my-brand")

        assert result is created
        self.repository.create.assert_called_once_with(
            original_url="https://example.com",
            short_code="my-brand",
            owner=owner,
        )
        self.generator.generate.assert_not_called()

    def test_free_user_cannot_use_a_custom_alias(self):
        owner = Mock(id=1, is_premium_tier=False)
        self.repository.count_active_by_owner.return_value = 0

        with pytest.raises(CustomAliasNotAllowedError):
            self.service.create("https://example.com", owner=owner, custom_alias="my-brand")

        self.repository.create.assert_not_called()

    def test_anonymous_owner_cannot_use_a_custom_alias(self):
        with pytest.raises(CustomAliasNotAllowedError):
            self.service.create("https://example.com", custom_alias="my-brand")

        self.repository.create.assert_not_called()

    def test_taken_alias_raises_even_for_a_premium_user(self):
        owner = Mock(id=1, is_premium_tier=True)
        self.repository.exists_by_short_code.return_value = True

        with pytest.raises(CustomAliasTakenError) as exc_info:
            self.service.create("https://example.com", owner=owner, custom_alias="my-brand")

        assert exc_info.value.alias == "my-brand"
        self.repository.create.assert_not_called()


class TestURLShortenerServiceDelete:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.service = URLShortenerService(repository=self.repository, generator=self.generator)

    def test_deletes_via_the_repository(self):
        url = Mock(id=1, short_code="abc1234", owner_id=9)

        self.service.delete(url)

        self.repository.delete.assert_called_once_with(url)

    def test_delete_owned_by_code_delegates_after_the_ownership_check(self):
        owner = Mock(id=9)
        url = Mock(id=1, short_code="abc1234", owner_id=9)
        self.repository.get_by_short_code.return_value = url

        self.service.delete_owned_by_code("abc1234", owner)

        self.repository.delete.assert_called_once_with(url)


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


class TestURLShortenerServiceRecordClick:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.analytics = Mock()
        self.geo_locator = Mock()
        self.service = URLShortenerService(
            repository=self.repository,
            generator=self.generator,
            analytics_repository=self.analytics,
            geo_locator=self.geo_locator,
        )

    def test_resolves_country_from_ip_when_not_given(self):
        url = Mock()
        self.geo_locator.country_code.return_value = "US"

        self.service.record_click(url, ip_address="8.8.8.8")

        self.geo_locator.country_code.assert_called_once_with("8.8.8.8")
        self.analytics.record_click.assert_called_once_with(
            url, ip_address="8.8.8.8", user_agent="", referer="", country="US"
        )

    def test_does_not_call_geo_locator_when_country_already_given(self):
        url = Mock()

        self.service.record_click(url, ip_address="8.8.8.8", country="GH")

        self.geo_locator.country_code.assert_not_called()
        self.analytics.record_click.assert_called_once_with(
            url, ip_address="8.8.8.8", user_agent="", referer="", country="GH"
        )

    def test_does_not_call_geo_locator_without_an_ip(self):
        url = Mock()

        self.service.record_click(url)

        self.geo_locator.country_code.assert_not_called()

    def test_works_without_a_geo_locator_configured(self):
        url = Mock()
        service = URLShortenerService(
            repository=self.repository,
            generator=self.generator,
            analytics_repository=self.analytics,
        )

        service.record_click(url, ip_address="8.8.8.8")

        self.analytics.record_click.assert_called_once_with(
            url, ip_address="8.8.8.8", user_agent="", referer="", country=""
        )


class TestURLShortenerServiceAnalyticsSummary:
    def setup_method(self) -> None:
        self.repository = Mock()
        self.generator = Mock()
        self.analytics = Mock()
        self.service = URLShortenerService(
            repository=self.repository,
            generator=self.generator,
            analytics_repository=self.analytics,
        )

    def test_assembles_stats_breakdowns_and_time_series(self):
        url = Mock(id=1, short_code="abc1234")
        stats = Mock(total_clicks=42)
        self.repository.get_aggregate_stats.return_value = stats
        self.analytics.get_country_breakdown.return_value = ["countries"]
        self.analytics.get_referrer_breakdown.return_value = ["referrers"]
        self.analytics.get_hourly_distribution.return_value = ["hourly"]
        self.analytics.get_recent_clicks.return_value = ["recent"]
        self.repository.get_click_time_series.return_value = [("2024-01-01", 5)]

        summary = self.service.get_analytics_summary(url, days=7)

        assert summary == {
            "url_id": 1,
            "short_code": "abc1234",
            "stats": stats,
            "countries": ["countries"],
            "referrers": ["referrers"],
            "hourly_distribution": ["hourly"],
            "recent_clicks": ["recent"],
            "time_series": [{"date": "2024-01-01", "clicks": 5}],
        }
        self.repository.get_click_time_series.assert_called_once_with(url, days=7)
