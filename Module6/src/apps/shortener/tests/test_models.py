"""Tests for the :class:`URL` model."""

from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.shortener.models import URL

pytestmark = pytest.mark.django_db


class TestURLModel:
    def test_can_create_url_without_owner(self):
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc1234",
        )
        assert url.pk is not None
        assert url.created_at is not None
        assert url.owner is None

    def test_can_create_url_with_owner(self, user):
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="own1234",
            owner=user,
        )
        assert url.owner == user
        assert user.urls.count() == 1

    def test_short_code_is_unique(self):
        URL.objects.create(original_url="https://a.example.com", short_code="dup1234")
        with pytest.raises(IntegrityError):
            URL.objects.create(
                original_url="https://b.example.com",
                short_code="dup1234",
            )

    def test_string_representation(self):
        url = URL.objects.create(
            original_url="https://example.com",
            short_code="abc1234",
        )
        rendered = str(url)
        assert "abc1234" in rendered
        assert "https://example.com" in rendered
