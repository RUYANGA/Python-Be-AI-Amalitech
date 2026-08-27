"""Shared fixtures for the shortener test suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

_REPO_ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="session", autouse=True)
def _apply_alembic_migrations_to_test_db(django_db_setup, django_db_blocker):
    """Bring the SQLAlchemy-owned tables up to date in the test database.

    ``urls``/``clicks``/``tags`` etc. are ``managed = False`` in Django, so
    Django's own ``migrate`` (which built the test database above) never
    touches them — their schema is owned by Alembic. Without this, the
    freshly created test database is missing any column added via an
    Alembic migration only (e.g. ``clicks.city``), even though the real
    dev database has it.
    """
    from django.conf import settings

    db = settings.DATABASES["default"]
    test_db_url = f"postgresql+psycopg2://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_db_url
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(_REPO_ROOT / "alembic.ini"))
        with django_db_blocker.unblock():
            command.upgrade(cfg, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="bob",
        email="bob@example.com",
        password="testpass123",
    )
