"""Persist rate limit counters for multi-instance deployments."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260618_0018"
down_revision = "20260618_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("bucket_key", sa.String(length=255), primary_key=True),
        sa.Column("window_start", sa.Float(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("rate_limit_buckets")
