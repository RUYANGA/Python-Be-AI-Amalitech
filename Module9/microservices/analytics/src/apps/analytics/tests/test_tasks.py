"""Tests for the write-behind ``track_click_task`` Celery task.

Exercised directly (not through the view) here — ``test_click_ingest_view``
already covers the HTTP contract; these tests focus on the task's own
behavior in isolation.
"""

from __future__ import annotations

import pytest

from apps.analytics.models import Click
from apps.analytics.tasks import track_click_task

pytestmark = pytest.mark.django_db


class TestTrackClickTask:
    def test_persists_a_click_with_the_resolved_country(self):
        track_click_task("abc1234", "8.8.8.8", "pytest", "https://ref.example")

        click = Click.objects.get(short_code="abc1234")
        assert click.ip_address == "8.8.8.8"
        assert click.user_agent == "pytest"
        assert click.referer == "https://ref.example"
        assert click.country == "US"

    def test_persists_a_click_without_an_ip_address(self):
        track_click_task("abc1234", None)

        click = Click.objects.get(short_code="abc1234")
        assert click.ip_address is None
        assert click.country == ""
