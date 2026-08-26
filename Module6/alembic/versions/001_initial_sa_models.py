"""Initial SQLAlchemy schema — mirrors Django models.

Uses ``IF NOT EXISTS`` so the migration is idempotent when Django
migrations have already created the same tables.

Revision ID: 001_initial_sa
Revises:
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_sa"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL NOT NULL,
    name VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
);
CREATE INDEX IF NOT EXISTS ix_tags_name ON tags (name);

CREATE TABLE IF NOT EXISTS urls (
    id SERIAL NOT NULL,
    original_url VARCHAR(2048) NOT NULL,
    short_code VARCHAR(10) NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '',
    owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    click_count INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    UNIQUE (short_code)
);
CREATE INDEX IF NOT EXISTS ix_urls_short_code ON urls (short_code);
CREATE INDEX IF NOT EXISTS ix_urls_owner_created ON urls (owner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_urls_click_count_desc ON urls (click_count DESC);
CREATE INDEX IF NOT EXISTS ix_urls_active_expires ON urls (is_active, expires_at);

CREATE TABLE IF NOT EXISTS url_tags (
    url_id INTEGER REFERENCES urls(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (url_id, tag_id)
);

CREATE TABLE IF NOT EXISTS clicks (
    id SERIAL NOT NULL,
    url_id INTEGER NOT NULL REFERENCES urls(id) ON DELETE CASCADE,
    ip_address VARCHAR(45),
    user_agent TEXT NOT NULL DEFAULT '',
    referer VARCHAR(2048) NOT NULL DEFAULT '',
    country VARCHAR(2) NOT NULL DEFAULT '',
    clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_clicks_url_clicked ON clicks (url_id, clicked_at DESC);
CREATE INDEX IF NOT EXISTS ix_clicks_country_clicked ON clicks (country, clicked_at DESC);
"""


def upgrade() -> None:
    op.execute(sa.text(_TABLES_SQL))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS clicks CASCADE;"))
    op.execute(sa.text("DROP TABLE IF EXISTS url_tags CASCADE;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_urls_active_expires;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_urls_click_count_desc;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_urls_owner_created;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_urls_short_code;"))
    op.execute(sa.text("DROP TABLE IF EXISTS urls CASCADE;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_tags_name;"))
    op.execute(sa.text("DROP TABLE IF EXISTS tags CASCADE;"))
