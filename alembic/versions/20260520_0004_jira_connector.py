"""jira connector

Revision ID: 20260520_0004
Revises: 20260518_0002
Create Date: 2026-05-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260520_0004"
down_revision = "20260518_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace_members",
        sa.Column("connector_manager", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "jira_user_connections",
        sa.Column("connection_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("atlassian_account_id", sa.String(length=255), nullable=True),
        sa.Column("account_email", sa.String(length=320), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_jira_user_connection_user_id"),
    )
    op.create_index("ix_jira_user_connections_user_id", "jira_user_connections", ["user_id"])
    op.create_index(
        "ix_jira_user_connections_atlassian_account_id",
        "jira_user_connections",
        ["atlassian_account_id"],
    )

    op.create_table(
        "jira_user_sites",
        sa.Column("site_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("cloud_id", sa.String(length=255), nullable=False),
        sa.Column("site_name", sa.String(length=255), nullable=False),
        sa.Column("site_url", sa.String(length=500), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.String(length=1000), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "cloud_id", name="uq_jira_user_site"),
    )
    op.create_index("ix_jira_user_sites_user_id", "jira_user_sites", ["user_id"])
    op.create_index("ix_jira_user_sites_cloud_id", "jira_user_sites", ["cloud_id"])

    op.create_table(
        "workspace_jira_sources",
        sa.Column("source_id", sa.String(length=96), primary_key=True),
        sa.Column("workspace_id", sa.String(length=96), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
        sa.Column("cloud_id", sa.String(length=255), nullable=False),
        sa.Column("site_name", sa.String(length=255), nullable=False),
        sa.Column("site_url", sa.String(length=500), nullable=False),
        sa.Column("project_id", sa.String(length=96), nullable=False),
        sa.Column("project_key", sa.String(length=64), nullable=False),
        sa.Column("project_name", sa.String(length=255), nullable=False),
        sa.Column("added_by_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_owner_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "cloud_id", "project_id", name="uq_workspace_jira_project"),
    )
    op.create_index("ix_workspace_jira_sources_workspace_id", "workspace_jira_sources", ["workspace_id"])
    op.create_index("ix_workspace_jira_sources_cloud_id", "workspace_jira_sources", ["cloud_id"])
    op.create_index("ix_workspace_jira_sources_project_id", "workspace_jira_sources", ["project_id"])
    op.create_index("ix_workspace_jira_sources_project_key", "workspace_jira_sources", ["project_key"])
    op.create_index("ix_workspace_jira_sources_added_by_user_id", "workspace_jira_sources", ["added_by_user_id"])
    op.create_index("ix_workspace_jira_sources_sync_owner_user_id", "workspace_jira_sources", ["sync_owner_user_id"])

    op.create_table(
        "jira_indexed_items",
        sa.Column("item_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(length=96), sa.ForeignKey("workspace_jira_sources.source_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.String(length=96), nullable=False),
        sa.Column("cloud_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=96), nullable=False),
        sa.Column("project_key", sa.String(length=64), nullable=False),
        sa.Column("issue_id", sa.String(length=96), nullable=False),
        sa.Column("issue_key", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("remote_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "item_type", "item_id", name="uq_jira_indexed_item"),
    )
    op.create_index("ix_jira_indexed_items_source_id", "jira_indexed_items", ["source_id"])
    op.create_index("ix_jira_indexed_items_workspace_id", "jira_indexed_items", ["workspace_id"])
    op.create_index("ix_jira_indexed_items_cloud_id", "jira_indexed_items", ["cloud_id"])
    op.create_index("ix_jira_indexed_items_project_id", "jira_indexed_items", ["project_id"])
    op.create_index("ix_jira_indexed_items_project_key", "jira_indexed_items", ["project_key"])
    op.create_index("ix_jira_indexed_items_issue_id", "jira_indexed_items", ["issue_id"])
    op.create_index("ix_jira_indexed_items_issue_key", "jira_indexed_items", ["issue_key"])
    op.create_index("ix_jira_indexed_items_item_type", "jira_indexed_items", ["item_type"])
    op.create_index("ix_jira_indexed_items_item_id", "jira_indexed_items", ["item_id"])

    op.create_table(
        "jira_visibility_cache",
        sa.Column("cache_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("cloud_id", sa.String(length=255), nullable=False),
        sa.Column("issue_id", sa.String(length=96), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.String(length=255), nullable=False),
        sa.Column("can_access", sa.Boolean(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "cloud_id", "issue_id", "item_type", "item_id", name="uq_jira_visibility_cache"),
    )
    op.create_index("ix_jira_visibility_cache_user_id", "jira_visibility_cache", ["user_id"])
    op.create_index("ix_jira_visibility_cache_cloud_id", "jira_visibility_cache", ["cloud_id"])
    op.create_index("ix_jira_visibility_cache_issue_id", "jira_visibility_cache", ["issue_id"])
    op.create_index("ix_jira_visibility_cache_expires_at", "jira_visibility_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_jira_visibility_cache_expires_at", table_name="jira_visibility_cache")
    op.drop_index("ix_jira_visibility_cache_issue_id", table_name="jira_visibility_cache")
    op.drop_index("ix_jira_visibility_cache_cloud_id", table_name="jira_visibility_cache")
    op.drop_index("ix_jira_visibility_cache_user_id", table_name="jira_visibility_cache")
    op.drop_table("jira_visibility_cache")

    op.drop_index("ix_jira_indexed_items_item_id", table_name="jira_indexed_items")
    op.drop_index("ix_jira_indexed_items_item_type", table_name="jira_indexed_items")
    op.drop_index("ix_jira_indexed_items_issue_key", table_name="jira_indexed_items")
    op.drop_index("ix_jira_indexed_items_issue_id", table_name="jira_indexed_items")
    op.drop_index("ix_jira_indexed_items_project_key", table_name="jira_indexed_items")
    op.drop_index("ix_jira_indexed_items_project_id", table_name="jira_indexed_items")
    op.drop_index("ix_jira_indexed_items_cloud_id", table_name="jira_indexed_items")
    op.drop_index("ix_jira_indexed_items_workspace_id", table_name="jira_indexed_items")
    op.drop_index("ix_jira_indexed_items_source_id", table_name="jira_indexed_items")
    op.drop_table("jira_indexed_items")

    op.drop_index("ix_workspace_jira_sources_sync_owner_user_id", table_name="workspace_jira_sources")
    op.drop_index("ix_workspace_jira_sources_added_by_user_id", table_name="workspace_jira_sources")
    op.drop_index("ix_workspace_jira_sources_project_key", table_name="workspace_jira_sources")
    op.drop_index("ix_workspace_jira_sources_project_id", table_name="workspace_jira_sources")
    op.drop_index("ix_workspace_jira_sources_cloud_id", table_name="workspace_jira_sources")
    op.drop_index("ix_workspace_jira_sources_workspace_id", table_name="workspace_jira_sources")
    op.drop_table("workspace_jira_sources")

    op.drop_index("ix_jira_user_sites_cloud_id", table_name="jira_user_sites")
    op.drop_index("ix_jira_user_sites_user_id", table_name="jira_user_sites")
    op.drop_table("jira_user_sites")

    op.drop_index("ix_jira_user_connections_atlassian_account_id", table_name="jira_user_connections")
    op.drop_index("ix_jira_user_connections_user_id", table_name="jira_user_connections")
    op.drop_table("jira_user_connections")

    op.drop_column("workspace_members", "connector_manager")
