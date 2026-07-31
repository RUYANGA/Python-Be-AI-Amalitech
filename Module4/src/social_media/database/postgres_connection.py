"""PostgreSQL connection manager.

Pools connections with psycopg2 and exposes a single cursor() context
manager: borrow a connection, run one or more statements, commit on success
or roll back on error, always return the connection to the pool. A caller
that issues several cur.execute() calls inside one `with` block gets one
atomic transaction for free — that's what the transactional follow relies on.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from social_media.config.settings import Settings
from social_media.utils.logger import get_logger

log = get_logger(__name__)

# Canonical DDL lives at the repo root (sql/ddl.sql) rather than inside the
# package — it's a first-class deliverable (see sql/, docs/database-design.md),
# not just an implementation detail.
SCHEMA_PATH = Path(__file__).resolve().parents[3] / "sql" / "ddl.sql"


class PostgresConnection:
    """PostgreSQL pooled connection — inject Settings rather than importing globally."""

    _instance: Optional["PostgresConnection"] = None

    def __new__(cls, settings: Settings) -> "PostgresConnection":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_pool(settings)
        return cls._instance

    def _init_pool(self, settings: Settings) -> None:
        """Build the connection pool and apply the canonical schema."""
        dsn = (
            f"host={settings.pg_host} port={settings.pg_port} "
            f"dbname={settings.pg_db} user={settings.pg_user} password={settings.pg_password}"
        )
        try:
            self._pool = ThreadedConnectionPool(settings.pg_pool_min, settings.pg_pool_max, dsn)
            with self.cursor() as cur:
                cur.execute(SCHEMA_PATH.read_text())
            log.info("Connected to PostgreSQL at %s:%s", settings.pg_host, settings.pg_port)
        except Exception as exc:
            log.error("PostgreSQL connection failed: %s", exc)
            raise

    @contextmanager
    def cursor(self):
        """Borrow a pooled connection; commit on success, roll back on error."""
        conn = self._pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def close(self) -> None:
        """Close every connection in the pool."""
        self._pool.closeall()
        log.info("PostgreSQL connection pool closed")
