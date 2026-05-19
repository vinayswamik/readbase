"""hierarchy graph

Revision ID: 20260518_0002
Revises: 20260518_0001
Create Date: 2026-05-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260518_0002"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hierarchy_connections")
    op.execute("DROP TABLE IF EXISTS hierarchy_nodes")

    op.create_table(
        "hierarchy_nodes",
        sa.Column("node_id", sa.String(length=96), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=96),
            sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("assigned_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "assigned_user_id", name="uq_hierarchy_node_assigned_user"),
    )
    op.create_index("ix_hierarchy_nodes_workspace_id", "hierarchy_nodes", ["workspace_id"])
    op.create_index("ix_hierarchy_nodes_assigned_user_id", "hierarchy_nodes", ["assigned_user_id"])
    op.create_index("ix_hierarchy_nodes_created_by_user_id", "hierarchy_nodes", ["created_by_user_id"])

    op.create_table(
        "hierarchy_connections",
        sa.Column("connection_id", sa.String(length=96), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=96),
            sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_node_id",
            sa.String(length=96),
            sa.ForeignKey("hierarchy_nodes.node_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "child_node_id",
            sa.String(length=96),
            sa.ForeignKey("hierarchy_nodes.node_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "parent_node_id", "child_node_id", name="uq_hierarchy_connection"),
        sa.UniqueConstraint("workspace_id", "child_node_id", name="uq_hierarchy_child_parent"),
    )
    op.create_index("ix_hierarchy_connections_workspace_id", "hierarchy_connections", ["workspace_id"])
    op.create_index("ix_hierarchy_connections_parent_node_id", "hierarchy_connections", ["parent_node_id"])
    op.create_index("ix_hierarchy_connections_child_node_id", "hierarchy_connections", ["child_node_id"])
    op.create_index(
        "ix_hierarchy_connections_created_by_user_id",
        "hierarchy_connections",
        ["created_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_hierarchy_connections_created_by_user_id", table_name="hierarchy_connections")
    op.drop_index("ix_hierarchy_connections_child_node_id", table_name="hierarchy_connections")
    op.drop_index("ix_hierarchy_connections_parent_node_id", table_name="hierarchy_connections")
    op.drop_index("ix_hierarchy_connections_workspace_id", table_name="hierarchy_connections")
    op.drop_table("hierarchy_connections")
    op.drop_index("ix_hierarchy_nodes_created_by_user_id", table_name="hierarchy_nodes")
    op.drop_index("ix_hierarchy_nodes_assigned_user_id", table_name="hierarchy_nodes")
    op.drop_index("ix_hierarchy_nodes_workspace_id", table_name="hierarchy_nodes")
    op.drop_table("hierarchy_nodes")
