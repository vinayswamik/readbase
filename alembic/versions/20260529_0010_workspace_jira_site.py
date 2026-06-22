"""workspace jira site

Revision ID: 20260529_0010
Revises: 20260529_0009
Create Date: 2026-05-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260529_0010"
down_revision = "20260529_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_jira_sites",
        sa.Column(
            "workspace_id",
            sa.String(length=96),
            sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("cloud_id", sa.String(length=255), nullable=False),
        sa.Column("site_name", sa.String(length=255), nullable=False),
        sa.Column("site_url", sa.String(length=500), nullable=False),
        sa.Column("connected_by_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspace_jira_sites_cloud_id", "workspace_jira_sites", ["cloud_id"])
    op.create_index(
        "ix_workspace_jira_sites_connected_by_user_id",
        "workspace_jira_sites",
        ["connected_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_jira_sites_connected_by_user_id", table_name="workspace_jira_sites")
    op.drop_index("ix_workspace_jira_sites_cloud_id", table_name="workspace_jira_sites")
    op.drop_table("workspace_jira_sites")
