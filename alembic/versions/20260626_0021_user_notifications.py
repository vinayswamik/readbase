"""user notifications for workspace events

Revision ID: 20260626_0021
Revises: 20260619_0020
Create Date: 2026-06-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260626_0021"
down_revision = "20260619_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_notifications",
        sa.Column("notification_id", sa.String(length=96), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=96), nullable=False),
        sa.Column("workspace_name", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.String(length=255), nullable=False),
        sa.Column("actor_name", sa.String(length=255), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("notification_id"),
    )
    op.create_index(
        "ix_user_notifications_recipient_user_id",
        "user_notifications",
        ["recipient_user_id"],
    )
    op.create_index(
        "ix_user_notifications_workspace_id",
        "user_notifications",
        ["workspace_id"],
    )
    op.create_index(
        "ix_user_notifications_created_at",
        "user_notifications",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_notifications_created_at", table_name="user_notifications")
    op.drop_index("ix_user_notifications_workspace_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_recipient_user_id", table_name="user_notifications")
    op.drop_table("user_notifications")
