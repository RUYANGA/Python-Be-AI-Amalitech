"""Shared fixtures for the users test suite."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="alice",
        first_name="Alice",
        last_name="Doe",
        email="alice@example.com",
        password="testpass123",
    )


@pytest.fixture
def inactive_user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="bob",
        email="bob@example.com",
        password="testpass123",
        is_active=False,
    )
