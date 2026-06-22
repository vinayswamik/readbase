"""org source registry

Revision ID: 20260619_0020
Revises: 20260618_0019
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260619_0020"
down_revision = "20260618_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_sources",
        sa.Column("source_id", sa.String(length=96), primary_key=True),
        sa.Column(
            "org_id",
            sa.String(length=96),
            sa.ForeignKey("organizations.org_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_key", sa.String(length=512), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "added_by_user_id",
            sa.String(length=255),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
        sa.Column(
            "sync_owner_user_id",
            sa.String(length=255),
            sa.ForeignKey("users.user_id"),
            nullable=True,
        ),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("org_id", "provider", "external_key", name="uq_org_source_identity"),
    )
    op.create_index("ix_org_sources_org_id", "org_sources", ["org_id"])
    op.create_index("ix_org_sources_provider", "org_sources", ["provider"])
    op.create_index("ix_org_sources_added_by_user_id", "org_sources", ["added_by_user_id"])
    op.create_index("ix_org_sources_sync_owner_user_id", "org_sources", ["sync_owner_user_id"])

    op.create_table(
        "workspace_source_subscriptions",
        sa.Column("subscription_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workspace_id",
            sa.String(length=96),
            sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(length=96),
            sa.ForeignKey("org_sources.source_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "added_by_user_id",
            sa.String(length=255),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id",
            "source_id",
            name="uq_workspace_source_subscription",
        ),
    )
    op.create_index(
        "ix_workspace_source_subscriptions_workspace_id",
        "workspace_source_subscriptions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_source_subscriptions_source_id",
        "workspace_source_subscriptions",
        ["source_id"],
    )
    op.create_index(
        "ix_workspace_source_subscriptions_added_by_user_id",
        "workspace_source_subscriptions",
        ["added_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_source_subscriptions_added_by_user_id",
        table_name="workspace_source_subscriptions",
    )
    op.drop_index("ix_workspace_source_subscriptions_source_id", table_name="workspace_source_subscriptions")
    op.drop_index(
        "ix_workspace_source_subscriptions_workspace_id",
        table_name="workspace_source_subscriptions",
    )
    op.drop_table("workspace_source_subscriptions")

    op.drop_index("ix_org_sources_sync_owner_user_id", table_name="org_sources")
    op.drop_index("ix_org_sources_added_by_user_id", table_name="org_sources")
    op.drop_index("ix_org_sources_provider", table_name="org_sources")
    op.drop_index("ix_org_sources_org_id", table_name="org_sources")
    op.drop_table("org_sources")
