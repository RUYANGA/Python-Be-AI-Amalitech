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
    """Build the Postgres URL from environment variables."""
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "url_shortener")
    user = os.getenv("DB_USER", "postgres")
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
