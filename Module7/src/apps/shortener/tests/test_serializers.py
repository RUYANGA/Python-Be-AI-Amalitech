"""Tests for the shortener API serializers."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.shortener.api.serializers import URLCreateSerializer, URLResponseSerializer
from apps.shortener.models import URL

pytestmark = pytest.mark.django_db


class TestURLCreateSerializer:
    def test_custom_alias_is_optional(self):
        serializer = URLCreateSerializer(data={"original_url": "https://example.com"})

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["custom_alias"] == ""

    @pytest.mark.parametrize("alias", ["my-link", "my_link_1", "abc", "1234567890"])
    def test_accepts_valid_aliases(self, alias):
        serializer = URLCreateSerializer(
            data={"original_url": "https://example.com", "custom_alias": alias}
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["custom_alias"] == alias

    @pytest.mark.parametrize(
        "alias",
        [
            "ab",  # too short
            "12345678901",  # too long
            "has space",
            "has/slash",
        ],
    )
    def test_rejects_invalid_aliases(self, alias):
        serializer = URLCreateSerializer(
            data={"original_url": "https://example.com", "custom_alias": alias}
        )

        assert not serializer.is_valid()
        assert "custom_alias" in serializer.errors


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
