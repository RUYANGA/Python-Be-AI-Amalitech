"""SQLAlchemy engine and session factory.

Reads connection parameters from Django's ``settings.DATABASES`` so
the engine always stays in sync with the Django configuration.

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


@lru_cache(maxsize=1)
def _build_url() -> str:
    """Build the database URL, preferring Django settings when available."""
    try:
        from django.conf import settings

        db = settings.DATABASES["default"]
        engine = db["ENGINE"]
        # Map django engine name to sqlalchemy driver
        driver_map = {
            "django.db.backends.postgresql": "postgresql+psycopg2",
            "django.db.backends.postgresql_psycopg2": "postgresql+psycopg2",
            "django.db.backends.mysql": "mysql+pymysql",
            "django.db.backends.sqlite3": "sqlite",
        }
        sa_driver = driver_map.get(engine, engine.replace("django.db.backends.", ""))
        return f"{sa_driver}://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"
    except ImportError:
        pass

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "url_shortener")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
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


def get_session(engine=None):
    """Convenience: return a new session instance."""
    return get_session_factory(engine)()
