"""admin member workspaces

Revision ID: 20260518_0001
Revises:
Create Date: 2026-05-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260518_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=255), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("email_key", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email_key", "users", ["email_key"], unique=True)

    op.create_table(
        "admin_approvals",
        sa.Column("approval_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("email_key", sa.String(length=320), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_admin_approvals_email_key", "admin_approvals", ["email_key"], unique=True)

    op.create_table(
        "workspaces",
        sa.Column("workspace_id", sa.String(length=96), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("name_key", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_user_id", "name_key", name="uq_workspace_owner_name"),
    )
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])

    op.create_table(
        "workspace_members",
        sa.Column("member_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workspace_id", sa.String(length=96), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("member_email", sa.String(length=320), nullable=False),
        sa.Column("member_email_key", sa.String(length=320), nullable=False),
        sa.Column("added_by_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "member_email_key", name="uq_workspace_member_email"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])
    op.create_index("ix_workspace_members_member_email_key", "workspace_members", ["member_email_key"])


def downgrade() -> None:
    op.drop_index("ix_workspace_members_member_email_key", table_name="workspace_members")
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_index("ix_workspaces_owner_user_id", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index("ix_admin_approvals_email_key", table_name="admin_approvals")
    op.drop_table("admin_approvals")
    op.drop_index("ix_users_email_key", table_name="users")
    op.drop_table("users")
