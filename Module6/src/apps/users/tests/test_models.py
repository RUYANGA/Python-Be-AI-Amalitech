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
