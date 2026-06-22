"""workspace invite expiry

Revision ID: 20260618_0016
Revises: 20260618_0015
Create Date: 2026-06-18
"""

from __future__ import annotations

from datetime import timedelta, timezone

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
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT invite_id, created_at FROM workspace_invites WHERE expires_at IS NULL")
    ).fetchall()
    for invite_id, created_at in rows:
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        expires_at = created_at + timedelta(days=7)
        connection.execute(
            sa.text(
                "UPDATE workspace_invites SET expires_at = :expires_at WHERE invite_id = :invite_id"
            ),
            {"expires_at": expires_at, "invite_id": invite_id},
        )


def downgrade() -> None:
    op.drop_column("workspace_invites", "expires_at")
