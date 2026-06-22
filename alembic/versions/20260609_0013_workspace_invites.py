"""workspace email invites with hierarchy metadata

Revision ID: 20260609_0013
Revises: 20260609_0012
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260609_0013"
down_revision = "20260609_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_invites",
        sa.Column("invite_id", sa.String(length=96), nullable=False),
        sa.Column("workspace_id", sa.String(length=96), nullable=False),
        sa.Column("invitee_email", sa.String(length=320), nullable=False),
        sa.Column("invitee_email_key", sa.String(length=320), nullable=False),
        sa.Column("invitee_name", sa.String(length=255), nullable=False),
        sa.Column("invitee_user_id", sa.String(length=255), nullable=True),
        sa.Column("invitor_user_id", sa.String(length=255), nullable=False),
        sa.Column("invitor_name", sa.String(length=255), nullable=False),
        sa.Column("invitor_designation", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("relation", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("node_display_name", sa.String(length=120), nullable=False),
        sa.Column("parent_node_id", sa.String(length=96), nullable=True),
        sa.Column("node_x", sa.Float(), nullable=False, server_default="0"),
        sa.Column("node_y", sa.Float(), nullable=False, server_default="0"),
        sa.Column("node_id", sa.String(length=96), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invitee_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["invitor_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["node_id"], ["hierarchy_nodes.node_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_node_id"], ["hierarchy_nodes.node_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("invite_id"),
    )
    op.create_index("ix_workspace_invites_workspace_id", "workspace_invites", ["workspace_id"])
    op.create_index("ix_workspace_invites_invitee_email_key", "workspace_invites", ["invitee_email_key"])
    op.create_index("ix_workspace_invites_invitee_user_id", "workspace_invites", ["invitee_user_id"])
    op.create_index("ix_workspace_invites_invitor_user_id", "workspace_invites", ["invitor_user_id"])
    op.create_index("ix_workspace_invites_node_id", "workspace_invites", ["node_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_invites_node_id", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_invitor_user_id", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_invitee_user_id", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_invitee_email_key", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_workspace_id", table_name="workspace_invites")
    op.drop_table("workspace_invites")
