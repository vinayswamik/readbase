"""workspace invite expiry

Revision ID: 20260618_0016
Revises: 20260618_0015
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260618_0016"
down_revision = "20260618_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace_invites",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE workspace_invites SET expires_at = datetime(created_at, '+7 days') "
        "WHERE expires_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("workspace_invites", "expires_at")
