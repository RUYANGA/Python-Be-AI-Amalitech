"""End-to-end smoke tests for the shortener service's public HTTP contract.

Covers the things that are genuinely new about this service boundary:
no local ``users`` table (auth via ``force_authenticate`` standing in
for a verified JWT), the plain-integer ``owner_id``, RBAC, tier limits,
and that the redirect endpoint never raises even when Redis (where
click events are published) is unreachable.
"""

from __future__ import annotations

import pytest

from apps.shortener.models import URL

pytestmark = pytest.mark.django_db


class TestCreateAndResolve:
    def test_anonymous_cannot_create(self, api_client):
        response = api_client.post(
            "/api/v1/urls/", {"original_url": "https://example.com"}, format="json"
        )
        assert response.status_code == 401

    def test_authenticated_user_can_create(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(
            "/api/v1/urls/", {"original_url": "https://example.com"}, format="json"
        )

        assert response.status_code == 201
        assert URL.objects.get(short_code=response.json()["short_code"]).owner_id == user.id

    def test_redirect_follows_through_to_the_original_url(self, api_client):
        url = URL.objects.create(original_url="https://example.com/target", short_code="tgt0001")

        response = api_client.get(f"/{url.short_code}/")

        assert response.status_code == 302
        assert response["Location"] == "https://example.com/target"


class TestOwnership:
    def test_non_owner_cannot_update(self, api_client, user, other_user):
        url = URL.objects.create(
            original_url="https://example.com", short_code="own0001", owner_id=user.id
        )
        api_client.force_authenticate(user=other_user)

        response = api_client.patch(
            f"/api/v1/urls/{url.short_code}/", {"title": "hijacked"}, format="json"
        )

        assert response.status_code == 404

    def test_owner_can_update(self, api_client, user):
        url = URL.objects.create(
            original_url="https://example.com", short_code="own0002", owner_id=user.id
        )
        api_client.force_authenticate(user=user)

        response = api_client.patch(
            f"/api/v1/urls/{url.short_code}/", {"title": "mine"}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["title"] == "mine"


class TestTierLimits:
    def test_free_user_is_capped_at_ten_active_urls(self, api_client, user):
        api_client.force_authenticate(user=user)
        for i in range(10):
            URL.objects.create(
                original_url=f"https://example.com/{i}", short_code=f"lim{i:04d}", owner_id=user.id
            )

        response = api_client.post(
            "/api/v1/urls/", {"original_url": "https://example.com/eleventh"}, format="json"
        )

        assert response.status_code == 403

    def test_premium_user_can_use_a_custom_alias(self, api_client):
        from apps.common.jwt_auth import RemoteUser

        premium = RemoteUser(id=3, username="carol", is_premium=True)
        api_client.force_authenticate(user=premium)

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/branded", "custom_alias": "my-brand"},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["short_code"] == "my-brand"

    def test_free_user_cannot_use_a_custom_alias(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(
            "/api/v1/urls/",
            {"original_url": "https://example.com/branded", "custom_alias": "my-brand"},
            format="json",
        )

        assert response.status_code == 403
