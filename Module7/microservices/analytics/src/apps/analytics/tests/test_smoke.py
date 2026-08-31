"""End-to-end smoke tests for the analytics service's public HTTP contract.

The one thing genuinely new here is the cross-service ownership check —
tests patch ``build_analytics_service`` to inject a service backed by a
mocked ``URLOwnershipClient``, standing in for a real call to the
shortener service.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from apps.analytics.api.services import AnalyticsService
from apps.analytics.models import Click

pytestmark = pytest.mark.django_db


class TestAnalyticsByCodeView:
    def test_rejects_non_premium_users(self, api_client, free_user):
        api_client.force_authenticate(user=free_user)

        response = api_client.get("/api/v1/analytics/abc1234/")

        assert response.status_code == 403

    def test_returns_404_when_not_owned(self, api_client, premium_user):
        api_client.force_authenticate(user=premium_user)
        ownership_client = Mock()
        ownership_client.get_owner_id.return_value = (True, 5, 999)  # owned by someone else
        service = AnalyticsService(repository=Mock(), ownership_client=ownership_client)

        with patch(
            "apps.analytics.api.views.analytics_by_code_view.build_analytics_service",
            return_value=service,
        ):
            response = api_client.get("/api/v1/analytics/abc1234/")

        assert response.status_code == 404

    def test_returns_the_summary_for_the_owner(self, api_client, premium_user):
        api_client.force_authenticate(user=premium_user)
        Click.objects.create(short_code="abc1234", country="US", referer="https://google.com")
        Click.objects.create(short_code="abc1234", country="US")

        ownership_client = Mock()
        ownership_client.get_owner_id.return_value = (True, 5, premium_user.id)
        service = AnalyticsService(repository=_real_repository(), ownership_client=ownership_client)

        with patch(
            "apps.analytics.api.views.analytics_by_code_view.build_analytics_service",
            return_value=service,
        ):
            response = api_client.get("/api/v1/analytics/abc1234/")

        assert response.status_code == 200
        body = response.json()
        assert body["url_id"] == 5
        assert body["stats"]["total_clicks"] == 2
        assert body["countries"] == [{"country": "US", "clicks": 2, "percentage": 100.0}]


def _real_repository():
    from apps.analytics.api.repositories.analytics_repository import (
        DjangoClickAnalyticsRepository,
    )

    return DjangoClickAnalyticsRepository()
