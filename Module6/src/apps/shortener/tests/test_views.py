"""Integration tests for the shortener API views."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.shortener.api.exceptions import ShortCodeGenerationError
from apps.shortener.models import URL
from database.connection import clear_session_factory_override, set_session_factory_override

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


@pytest.fixture(autouse=True)
def _sqlalchemy_shares_django_connection(db):
    """Bind the SQLAlchemy layer to Django's own test-transaction connection.

    Django's ``db`` fixture wraps each test in an uncommitted transaction
    that is rolled back afterwards. These view tests read/write through a
    separate SQLAlchemy engine; without this, that engine opens its own
    connection and can't see data the other ORM just wrote (or vice
    versa). Sharing the connection — with SQLAlchemy commits downgraded to
    SAVEPOINTs via ``join_transaction_mode`` — keeps both ORMs looking at
    the same in-progress transaction, so no real commit is ever needed.

    ``pool_reset_on_return=None`` stops SQLAlchemy from issuing a
    ``ROLLBACK``/``COMMIT`` on this connection when checking it in or
    disposing the pool — Django owns this connection's lifecycle, not us.
    The sessionmaker is bound to one already-``begin()``'d ``Connection``
    (not the ``Engine``): binding to the engine would make every new
    Session check out its own wrapper and, finding no transaction it
    recognizes, defensively roll back — which would wipe out whatever
    Django had just written.
    """
    from django.db import connection as django_connection

    django_connection.ensure_connection()
    raw_connection = django_connection.connection

    engine = create_engine(
        "postgresql+psycopg2://",
        creator=lambda: raw_connection,
        poolclass=StaticPool,
        pool_reset_on_return=None,
    )
    sa_connection = engine.connect()
    sa_connection.begin()
    factory = sessionmaker(bind=sa_connection, join_transaction_mode="create_savepoint")
    set_session_factory_override(factory)
    try:
        yield
    finally:
        clear_session_factory_override()
        sa_connection.close()


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
            mock_build.return_value.shorten.side_effect = ShortCodeGenerationError()

            response = api_client.post(
                "/api/v1/urls/",
                {"original_url": "https://example.com/fail"},
                format="json",
            )

        assert response.status_code == 500


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
