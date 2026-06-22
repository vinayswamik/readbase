"""workspace slack teams

Revision ID: 20260618_0019
Revises: 20260618_0018
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260618_0019"
down_revision = "20260618_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_slack_teams",
        sa.Column("team_link_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workspace_id",
            sa.String(length=96),
            sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("team_id", sa.String(length=255), nullable=False),
        sa.Column("team_name", sa.String(length=255), nullable=False),
        sa.Column("team_domain", sa.String(length=255), nullable=True),
        sa.Column(
            "linked_by_user_id",
            sa.String(length=255),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "team_id", name="uq_workspace_slack_team"),
    )
    op.create_index("ix_workspace_slack_teams_workspace_id", "workspace_slack_teams", ["workspace_id"])
    op.create_index("ix_workspace_slack_teams_team_id", "workspace_slack_teams", ["team_id"])
    op.create_index(
        "ix_workspace_slack_teams_linked_by_user_id",
        "workspace_slack_teams",
        ["linked_by_user_id"],
    )

    op.execute(
        """
        INSERT INTO workspace_slack_teams (
            workspace_id,
            team_id,
            team_name,
            team_domain,
            linked_by_user_id,
            linked_at,
            updated_at
        )
        SELECT
            workspace_id,
            team_id,
            MIN(team_name),
            MIN(team_domain),
            MIN(added_by_user_id),
            MIN(created_at),
            MIN(created_at)
        FROM workspace_slack_sources
        GROUP BY workspace_id, team_id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_slack_teams_linked_by_user_id", table_name="workspace_slack_teams")
    op.drop_index("ix_workspace_slack_teams_team_id", table_name="workspace_slack_teams")
    op.drop_index("ix_workspace_slack_teams_workspace_id", table_name="workspace_slack_teams")
    op.drop_table("workspace_slack_teams")
