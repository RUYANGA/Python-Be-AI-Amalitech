"""Add is_premium and tier to users, city to clicks.

Revision ID: 002_premium_tier_city
Revises: 001_initial_sa
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_premium_tier_city"
down_revision: str = "001_initial_sa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS tier VARCHAR(20) NOT NULL DEFAULT 'free'"
        )
    )
    op.execute(
        sa.text("ALTER TABLE clicks ADD COLUMN IF NOT EXISTS city VARCHAR(100) NOT NULL DEFAULT ''")
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE clicks DROP COLUMN IF EXISTS city"))
    op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS tier"))
    op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS is_premium"))
