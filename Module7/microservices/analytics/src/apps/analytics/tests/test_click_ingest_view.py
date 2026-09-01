"""Tests for the internal click-ingestion endpoint.

Covers the REST contract that replaced the Kafka ``clicks`` topic and
``consume_clicks``: authenticated with ``X-Internal-Token``, resolves
geo from the IP, and persists a ``Click`` row synchronously.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.analytics.api.exceptions import RepositoryError
from apps.analytics.models import Click

pytestmark = pytest.mark.django_db


class TestClickIngestView:
    def test_rejects_a_request_without_the_internal_token(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.post(
            "/api/v1/internal/clicks/", {"short_code": "abc1234"}, format="json"
        )

        assert response.status_code == 401
        assert Click.objects.count() == 0

    def test_rejects_a_request_with_the_wrong_internal_token(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.post(
            "/api/v1/internal/clicks/",
            {"short_code": "abc1234"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="wrong",
        )

        assert response.status_code == 401
        assert Click.objects.count() == 0

    def test_records_a_click_with_the_resolved_country(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.post(
            "/api/v1/internal/clicks/",
            {
                "short_code": "abc1234",
                "ip_address": "8.8.8.8",
                "user_agent": "pytest",
                "referer": "https://ref.example",
            },
            format="json",
            HTTP_X_INTERNAL_TOKEN="shared-secret",
        )

        assert response.status_code == 204
        click = Click.objects.get(short_code="abc1234")
        assert click.ip_address == "8.8.8.8"
        assert click.user_agent == "pytest"
        assert click.referer == "https://ref.example"
        assert click.country == "US"

    def test_records_a_click_without_an_ip_address(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.post(
            "/api/v1/internal/clicks/",
            {"short_code": "abc1234"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="shared-secret",
        )

        assert response.status_code == 204
        click = Click.objects.get(short_code="abc1234")
        assert click.ip_address is None
        assert click.country == ""

    def test_rejects_a_payload_without_a_short_code(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        response = api_client.post(
            "/api/v1/internal/clicks/",
            {},
            format="json",
            HTTP_X_INTERNAL_TOKEN="shared-secret",
        )

        assert response.status_code == 400
        assert Click.objects.count() == 0

    def test_returns_500_when_the_repository_fails(self, api_client, settings):
        settings.INTERNAL_SERVICE_TOKEN = "shared-secret"

        with patch(
            "apps.analytics.api.views.click_ingest_view.DjangoClickAnalyticsRepository"
        ) as mock_repository_cls:
            mock_repository_cls.return_value.record_click.side_effect = RepositoryError(
                "record_click", short_code="abc1234"
            )

            response = api_client.post(
                "/api/v1/internal/clicks/",
                {"short_code": "abc1234"},
                format="json",
                HTTP_X_INTERNAL_TOKEN="shared-secret",
            )

        assert response.status_code == 500
