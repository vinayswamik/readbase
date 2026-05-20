"""workspace connectors

Revision ID: 20260519_0003
Revises: 20260518_0002
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260519_0003"
down_revision = "20260518_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_connectors",
        sa.Column("connector_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workspace_id",
            sa.String(length=96),
            sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("connector_id", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "connector_id", name="uq_workspace_connector"),
    )
    op.create_index("ix_workspace_connectors_workspace_id", "workspace_connectors", ["workspace_id"])
    op.create_index("ix_workspace_connectors_connector_id", "workspace_connectors", ["connector_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_connectors_connector_id", table_name="workspace_connectors")
    op.drop_index("ix_workspace_connectors_workspace_id", table_name="workspace_connectors")
    op.drop_table("workspace_connectors")
