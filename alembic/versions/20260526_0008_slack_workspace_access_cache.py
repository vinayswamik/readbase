"""slack workspace access cache

Revision ID: 20260526_0008
Revises: 20260521_0007
Create Date: 2026-05-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260526_0008"
down_revision = "20260521_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_slack_access_cache",
        sa.Column("cache_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workspace_id", sa.String(length=96), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.String(length=255), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("can_access", sa.Boolean(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", "team_id", "channel_id", name="uq_workspace_slack_access_cache"),
    )
    op.create_index("ix_workspace_slack_access_cache_workspace_id", "workspace_slack_access_cache", ["workspace_id"])
    op.create_index("ix_workspace_slack_access_cache_user_id", "workspace_slack_access_cache", ["user_id"])
    op.create_index("ix_workspace_slack_access_cache_team_id", "workspace_slack_access_cache", ["team_id"])
    op.create_index("ix_workspace_slack_access_cache_channel_id", "workspace_slack_access_cache", ["channel_id"])
    op.create_index("ix_workspace_slack_access_cache_expires_at", "workspace_slack_access_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_workspace_slack_access_cache_expires_at", table_name="workspace_slack_access_cache")
    op.drop_index("ix_workspace_slack_access_cache_channel_id", table_name="workspace_slack_access_cache")
    op.drop_index("ix_workspace_slack_access_cache_team_id", table_name="workspace_slack_access_cache")
    op.drop_index("ix_workspace_slack_access_cache_user_id", table_name="workspace_slack_access_cache")
    op.drop_index("ix_workspace_slack_access_cache_workspace_id", table_name="workspace_slack_access_cache")
    op.drop_table("workspace_slack_access_cache")
