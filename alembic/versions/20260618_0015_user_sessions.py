"""Opaque Postgres-backed user sessions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260618_0015"
down_revision = "20260609_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("session_id", sa.String(length=96), primary_key=True),
        sa.Column("session_token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_from_session_id", sa.String(length=96), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_sessions_session_token_hash", "user_sessions", ["session_token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_session_token_hash", table_name="user_sessions")
    op.drop_table("user_sessions")
