"""Integration tests for the shortener API views."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.shortener.api.exceptions import RepositoryError, ShortCodeGenerationError
from apps.shortener.models import URL

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_url_cache():
    """Flush cached URL entries before and after each test.

    ``CachedURLRepository`` writes to real Redis on every read/create, but
    those writes aren't part of the DB transaction these tests roll back —
    so without this, a short code reused across two test runs (or within
    the same TTL window) can serve a stale cached row from an earlier,
    already-rolled-back test.
    """
    from apps.shortener.api.cache.redis_client import get_redis_client

    client = get_redis_client()
    client.flush_pattern("url:*")
    yield
    client.flush_pattern("url:*")


class TestURLCreateView:
    def test_rejects_anonymous_requests(self, api_client):
        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/some/path"},
            format="json",
        )
        assert response.status_code == 401

    def test_creates_short_url_owned_by_authenticated_user(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/owned"},
            format="json",
        )

        assert response.status_code == 201
        body = response.json()
        assert body["original_url"] == "https://example.com/owned"
        assert len(body["short_code"]) == 7
        assert body["short_url"].endswith(f"/{body['short_code']}/")
        url = URL.objects.get(short_code=body["short_code"])
        assert url.owner == user

    def test_rejects_invalid_url(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "not a url"},
            format="json",
        )
        assert response.status_code == 400

    def test_rejects_missing_field(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post("/api/v1/urls/", {}, format="json")
        assert response.status_code == 400
        assert "original_url" in response.json()

    def test_returns_500_when_short_code_generation_fails(self, api_client, user):
        api_client.force_authenticate(user=user)

        with patch("apps.shortener.api.views.base_view.build_url_service") as mock_build:
            mock_build.return_value.create.side_effect = ShortCodeGenerationError()

            response = api_client.post(
                "/api/v1/urls/",
                {"original_url": "https://example.com/fail"},
                format="json",
            )

        assert response.status_code == 500

    def test_returns_403_when_free_user_is_at_the_active_url_limit(self, api_client, user):
        api_client.force_authenticate(user=user)
        for i in range(10):
            URL.objects.create(
                original_url=f"https://existing.example.com/{i}",
                short_code=f"lim{i:04d}",
                owner=user,
            )

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/one-too-many"},
            format="json",
        )

        assert response.status_code == 403
        assert "10 active URLs" in response.json()["detail"]

    def test_premium_user_is_not_limited(self, api_client, user):
        user.is_premium = True
        user.save()
        api_client.force_authenticate(user=user)
        for i in range(10):
            URL.objects.create(
                original_url=f"https://existing.example.com/{i}",
                short_code=f"pre{i:04d}",
                owner=user,
            )

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/still-fine"},
            format="json",
        )

        assert response.status_code == 201

    def test_premium_user_can_request_a_custom_alias(self, api_client, user):
        user.is_premium = True
        user.save()
        api_client.force_authenticate(user=user)

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/branded", "custom_alias": "my-brand"},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["short_code"] == "my-brand"

    def test_free_user_cannot_request_a_custom_alias(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/branded", "custom_alias": "my-brand"},
            format="json",
        )

        assert response.status_code == 403
        assert "premium" in response.json()["detail"].lower()

    def test_taken_alias_returns_409(self, api_client, user, other_user):
        other_user.is_premium = True
        other_user.save()
        api_client.force_authenticate(user=other_user)
        api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/first", "custom_alias": "my-brand"},
            format="json",
        )

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/second", "custom_alias": "my-brand"},
            format="json",
        )

        assert response.status_code == 409


class TestURLResolveView:
    def test_returns_original_url(self, api_client):
        url = URL.objects.create(original_url="https://example.com/target", short_code="tgt1234")

        response = api_client.get(f"/api/v1/{url.short_code}/")

        assert response.status_code == 200
        assert response.json()["original_url"] == "https://example.com/target"
        assert "Location" not in response

    def test_returns_404_for_unknown_code(self, api_client):
        response = api_client.get("/api/v1/nonexist/")
        assert response.status_code == 404


class TestURLRedirectView:
    def test_redirects_to_original_url(self, api_client):
        url = URL.objects.create(original_url="https://example.com/target", short_code="tgt1234")

        response = api_client.get(f"/{url.short_code}/")

        assert response.status_code == 302
        assert response["Location"] == "https://example.com/target"

    def test_increments_click_count(self, api_client):
        url = URL.objects.create(original_url="https://example.com/target", short_code="tgt1234")

        api_client.get(f"/{url.short_code}/")

        url.refresh_from_db()
        assert url.click_count == 1

    def test_returns_404_for_unknown_code(self, api_client):
        response = api_client.get("/nonexist/")
        assert response.status_code == 404


class TestURLListView:
    def test_rejects_anonymous_requests(self, api_client):
        response = api_client.get("/api/v1/urls/mine/")
        assert response.status_code == 401

    def test_lists_only_my_urls(self, api_client, user, other_user):
        URL.objects.create(
            original_url="https://mine.example.com", short_code="mine001", owner=user
        )
        URL.objects.create(
            original_url="https://not-mine.example.com", short_code="theirs01", owner=other_user
        )
        api_client.force_authenticate(user=user)

        response = api_client.get("/api/v1/urls/mine/")

        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) == 1
        assert body["results"][0]["short_code"] == "mine001"

    def test_returns_500_when_listing_fails(self, api_client, user):
        api_client.force_authenticate(user=user)

        with patch("apps.shortener.api.views.base_view.build_url_service") as mock_build:
            mock_build.return_value.list_with_filters.side_effect = RepositoryError(
                "list_with_filters"
            )

            response = api_client.get("/api/v1/urls/mine/")

        assert response.status_code == 500

    def test_filters_by_tag_case_and_whitespace_insensitively(self, api_client, user):
        api_client.force_authenticate(user=user)
        create_response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://tagged.example.com", "tags": ["Work"]},
            format="json",
        )
        assert create_response.status_code == 201

        response = api_client.get("/api/v1/urls/mine/", {"tag": " WORK "})

        assert response.status_code == 200
        assert response.json()["count"] == 1


class TestURLByCodeUpdate:
    def test_rejects_anonymous_requests(self, api_client, user):
        url = URL.objects.create(
            original_url="https://old.example.com", short_code="upd0001", owner=user
        )

        response = api_client.patch(
            f"/api/v1/urls/{url.short_code}/",
            {"original_url": "https://new.example.com"},
            format="json",
        )

        assert response.status_code == 401

    def test_owner_can_update(self, api_client, user):
        url = URL.objects.create(
            original_url="https://old.example.com", short_code="upd0002", owner=user
        )
        api_client.force_authenticate(user=user)

        response = api_client.patch(
            f"/api/v1/urls/{url.short_code}/",
            {"original_url": "https://new.example.com"},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["original_url"] == "https://new.example.com"
        url.refresh_from_db()
        assert url.original_url == "https://new.example.com"

    def test_non_owner_gets_404(self, api_client, user, other_user):
        url = URL.objects.create(
            original_url="https://old.example.com", short_code="upd0003", owner=other_user
        )
        api_client.force_authenticate(user=user)

        response = api_client.patch(
            f"/api/v1/urls/{url.short_code}/",
            {"original_url": "https://new.example.com"},
            format="json",
        )

        assert response.status_code == 404
        url.refresh_from_db()
        assert url.original_url == "https://old.example.com"

    def test_returns_404_for_unknown_code(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.patch(
            "/api/v1/urls/nonexist/",
            {"original_url": "https://new.example.com"},
            format="json",
        )

        assert response.status_code == 404

    def test_rejects_invalid_url(self, api_client, user):
        url = URL.objects.create(
            original_url="https://old.example.com", short_code="upd0004", owner=user
        )
        api_client.force_authenticate(user=user)

        response = api_client.patch(
            f"/api/v1/urls/{url.short_code}/", {"original_url": "not a url"}, format="json"
        )

        assert response.status_code == 400


class TestURLByCodeDelete:
    def test_rejects_anonymous_requests(self, api_client, user):
        url = URL.objects.create(
            original_url="https://old.example.com", short_code="del0001", owner=user
        )

        response = api_client.delete(f"/api/v1/urls/{url.short_code}/")

        assert response.status_code == 401
        assert URL.objects.filter(pk=url.pk).exists()

    def test_owner_can_delete(self, api_client, user):
        url = URL.objects.create(
            original_url="https://old.example.com", short_code="del0002", owner=user
        )
        api_client.force_authenticate(user=user)

        response = api_client.delete(f"/api/v1/urls/{url.short_code}/")

        assert response.status_code == 200
        assert response.json()["message"] == "URL deleted successfully."
        assert not URL.objects.filter(pk=url.pk).exists()

    def test_non_owner_gets_404(self, api_client, user, other_user):
        url = URL.objects.create(
            original_url="https://old.example.com", short_code="del0003", owner=other_user
        )
        api_client.force_authenticate(user=user)

        response = api_client.delete(f"/api/v1/urls/{url.short_code}/")

        assert response.status_code == 404
        assert URL.objects.filter(pk=url.pk).exists()

    def test_returns_404_for_unknown_code(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.delete("/api/v1/urls/nonexist/")

        assert response.status_code == 404


class TestURLAnalyticsByCodeView:
    def test_rejects_non_premium_users(self, api_client, user):
        url = URL.objects.create(
            original_url="https://analytics.example.com", short_code="ana0001", owner=user
        )
        api_client.force_authenticate(user=user)

        response = api_client.get(f"/api/v1/analytics/{url.short_code}/")

        assert response.status_code == 403

    def test_returns_the_full_summary_for_the_owner(self, api_client, user):
        user.is_premium = True
        user.save()
        url = URL.objects.create(
            original_url="https://analytics.example.com", short_code="ana0002", owner=user
        )
        api_client.force_authenticate(user=user)

        response = api_client.get(f"/api/v1/analytics/{url.short_code}/")

        assert response.status_code == 200
        body = response.json()
        assert body["url_id"] == url.id
        assert body["short_code"] == "ana0002"
        assert body["stats"]["total_clicks"] == 0
        assert body["countries"] == []
        assert body["referrers"] == []
        assert len(body["hourly_distribution"]) == 24
        assert all(hour["clicks"] == 0 for hour in body["hourly_distribution"])
        assert body["recent_clicks"] == []
        assert body["time_series"] == []

    def test_non_owner_gets_404(self, api_client, user, other_user):
        user.is_premium = True
        user.save()
        url = URL.objects.create(
            original_url="https://analytics.example.com", short_code="ana0003", owner=other_user
        )
        api_client.force_authenticate(user=user)

        response = api_client.get(f"/api/v1/analytics/{url.short_code}/")

        assert response.status_code == 404
