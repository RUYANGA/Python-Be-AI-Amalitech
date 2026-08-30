"""Tests for the custom :class:`User` model."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


class TestUserModel:
    def test_can_create_user(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="carol", password="testpass123")
        assert user.pk is not None
        assert user.check_password("testpass123")

    def test_string_representation(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="carol", password="testpass123")
        assert str(user) == "carol"


class TestUserIsPremiumTier:
    def test_free_tier_default_is_not_premium(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="carol", password="testpass123")
        assert user.is_premium_tier is False

    def test_is_premium_flag_grants_premium(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="carol", password="testpass123", is_premium=True
        )
        assert user.is_premium_tier is True

    @pytest.mark.parametrize("tier", ["pro", "enterprise"])
    def test_premium_tier_grants_premium(self, tier):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="carol", password="testpass123", tier=tier)
        assert user.is_premium_tier is True

    @pytest.mark.parametrize("tier", ["free", "basic"])
    def test_non_premium_tier_is_not_premium(self, tier):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="carol", password="testpass123", tier=tier)
        assert user.is_premium_tier is False
