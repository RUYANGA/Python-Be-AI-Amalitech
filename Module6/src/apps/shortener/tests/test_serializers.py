"""Tests for the shortener API serializers."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.shortener.api.serializers import URLResponseSerializer
from apps.shortener.models import URL

pytestmark = pytest.mark.django_db


class TestURLResponseSerializer:
    def test_short_url_uses_absolute_uri_with_request(self, rf):
        url = URL.objects.create(original_url="https://example.com", short_code="abc1234")
        request = rf.get("/")

        data = URLResponseSerializer(url, context={"request": request}).data

        expected_path = reverse("url-redirect", kwargs={"short_code": url.short_code})
        assert data["short_url"] == request.build_absolute_uri(expected_path)

    def test_short_url_falls_back_to_path_without_request(self):
        url = URL.objects.create(original_url="https://example.com", short_code="abc1234")

        data = URLResponseSerializer(url).data

        assert data["short_url"] == reverse("url-redirect", kwargs={"short_code": url.short_code})
