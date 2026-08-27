"""Fix foreign key constraints to use ON DELETE CASCADE.

Django's migration 0003 fixed the URLs -> users FK, but the clicks -> urls
and urls_tags -> urls/tags FKs still lack CASCADE.  This migration ensures
all shortener FKs use ON DELETE CASCADE.

Revision ID: 003_fix_fk_cascade
Revises: 002_premium_tier_city
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_fix_fk_cascade"
down_revision: str = "002_premium_tier_city"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("ALTER TABLE clicks DROP CONSTRAINT IF EXISTS clicks_url_id_2479f916_fk_urls_id")
    )
    op.execute(
        sa.text(
            "ALTER TABLE clicks ADD CONSTRAINT clicks_url_id_fk "
            "FOREIGN KEY (url_id) REFERENCES urls(id) "
            "ON DELETE CASCADE"
        )
    )

    op.execute(
        sa.text(
            "ALTER TABLE urls_tags DROP CONSTRAINT IF EXISTS urls_tags_url_id_b984a79a_fk_urls_id"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE urls_tags ADD CONSTRAINT urls_tags_url_id_fk "
            "FOREIGN KEY (url_id) REFERENCES urls(id) "
            "ON DELETE CASCADE"
        )
    )

    op.execute(
        sa.text(
            "ALTER TABLE urls_tags DROP CONSTRAINT IF EXISTS urls_tags_tag_id_b9e0d8b0_fk_tags_id"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE urls_tags ADD CONSTRAINT urls_tags_tag_id_fk "
            "FOREIGN KEY (tag_id) REFERENCES tags(id) "
            "ON DELETE CASCADE"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE clicks DROP CONSTRAINT IF EXISTS clicks_url_id_fk"))
    op.execute(sa.text("ALTER TABLE urls_tags DROP CONSTRAINT IF EXISTS urls_tags_url_id_fk"))
    op.execute(sa.text("ALTER TABLE urls_tags DROP CONSTRAINT IF EXISTS urls_tags_tag_id_fk"))
