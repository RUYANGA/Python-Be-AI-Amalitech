"""SQLAlchemy engine and session factory.

Reads connection parameters from Django's ``settings.DATABASES`` so
the engine always stays in sync with the Django configuration —
including the swapped-in test database name/credentials that
pytest-django uses while running tests. Falls back to ``.env`` /
environment variables when Django isn't set up (e.g. Alembic).

Usage::

    from database.connection import get_session
    session = get_session()
    urls = session.query(URLModel).all()
    session.close()
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base class shared by all SQLAlchemy models."""


_DRIVER_MAP = {
    "django.db.backends.postgresql": "postgresql+psycopg2",
    "django.db.backends.postgresql_psycopg2": "postgresql+psycopg2",
}


def _build_url() -> str:
    """Build the database URL, preferring Django settings when available."""
    try:
        from django.conf import settings

        db = settings.DATABASES["default"]
        driver = _DRIVER_MAP[db["ENGINE"]]
        return f"{driver}://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"
    except ImportError:
        pass

    from decouple import config

    password = config("DB_PASSWORD", default="")
    host = config("DB_HOST", default="localhost")
    port = config("DB_PORT", default="5432")
    name = config("DB_NAME", default="url_shortener")
    user = config("DB_USER", default="postgres")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


@lru_cache(maxsize=1)
def get_engine(url: str | None = None):
    """Return a cached SQLAlchemy engine.

    Uses ``NullPool`` in test / Alembic contexts to avoid holding
    connections open across fixture boundaries.
    """
    engine = create_engine(
        url or _build_url(),
        poolclass=NullPool,
        echo=os.getenv("SQL_ECHO", "0") == "1",
    )
    logger.debug("db.engine_initialized url=%s", url or _build_url())
    return engine


@lru_cache(maxsize=1)
def get_session_factory(engine=None):
    """Return a session factory bound to the engine."""
    return sessionmaker(bind=engine or get_engine())


_session_factory_override: sessionmaker | None = None


def set_session_factory_override(factory: sessionmaker) -> None:
    """Route :func:`get_session` through ``factory`` instead of the real engine.

    Used by tests to make the SQLAlchemy layer share Django's own test
    connection/transaction, so writes made through either ORM are visible
    to the other within the same test.
    """
    global _session_factory_override
    _session_factory_override = factory


def clear_session_factory_override() -> None:
    global _session_factory_override
    _session_factory_override = None


def get_session(engine=None):
    """Convenience: return a new session instance."""
    if _session_factory_override is not None:
        return _session_factory_override()
    return get_session_factory(engine)()
