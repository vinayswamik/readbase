"""slack connector

Revision ID: 20260520_0006
Revises: 20260520_0005
Create Date: 2026-05-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260520_0006"
down_revision = "20260520_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slack_user_connections",
        sa.Column("connection_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("slack_user_id", sa.String(length=255), nullable=False),
        sa.Column("team_id", sa.String(length=255), nullable=False),
        sa.Column("team_name", sa.String(length=255), nullable=False),
        sa.Column("team_domain", sa.String(length=255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "team_id", name="uq_slack_user_connection_team"),
    )
    op.create_index("ix_slack_user_connections_user_id", "slack_user_connections", ["user_id"])
    op.create_index("ix_slack_user_connections_slack_user_id", "slack_user_connections", ["slack_user_id"])
    op.create_index("ix_slack_user_connections_team_id", "slack_user_connections", ["team_id"])

    op.create_table(
        "workspace_slack_sources",
        sa.Column("source_id", sa.String(length=96), primary_key=True),
        sa.Column("workspace_id", sa.String(length=96), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.String(length=255), nullable=False),
        sa.Column("team_name", sa.String(length=255), nullable=False),
        sa.Column("team_domain", sa.String(length=255), nullable=True),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_name", sa.String(length=255), nullable=False),
        sa.Column("channel_is_private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("added_by_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_owner_user_id", sa.String(length=255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_ts", sa.String(length=64), nullable=True),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "team_id", "channel_id", name="uq_workspace_slack_channel"),
    )
    op.create_index("ix_workspace_slack_sources_workspace_id", "workspace_slack_sources", ["workspace_id"])
    op.create_index("ix_workspace_slack_sources_team_id", "workspace_slack_sources", ["team_id"])
    op.create_index("ix_workspace_slack_sources_channel_id", "workspace_slack_sources", ["channel_id"])
    op.create_index("ix_workspace_slack_sources_added_by_user_id", "workspace_slack_sources", ["added_by_user_id"])
    op.create_index("ix_workspace_slack_sources_sync_owner_user_id", "workspace_slack_sources", ["sync_owner_user_id"])

    op.create_table(
        "slack_indexed_items",
        sa.Column("item_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(length=96), sa.ForeignKey("workspace_slack_sources.source_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.String(length=96), nullable=False),
        sa.Column("team_id", sa.String(length=255), nullable=False),
        sa.Column("team_name", sa.String(length=255), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_name", sa.String(length=255), nullable=False),
        sa.Column("message_ts", sa.String(length=64), nullable=False),
        sa.Column("thread_ts", sa.String(length=64), nullable=True),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("remote_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "item_type", "item_id", name="uq_slack_indexed_item"),
    )
    op.create_index("ix_slack_indexed_items_source_id", "slack_indexed_items", ["source_id"])
    op.create_index("ix_slack_indexed_items_workspace_id", "slack_indexed_items", ["workspace_id"])
    op.create_index("ix_slack_indexed_items_team_id", "slack_indexed_items", ["team_id"])
    op.create_index("ix_slack_indexed_items_channel_id", "slack_indexed_items", ["channel_id"])
    op.create_index("ix_slack_indexed_items_message_ts", "slack_indexed_items", ["message_ts"])
    op.create_index("ix_slack_indexed_items_thread_ts", "slack_indexed_items", ["thread_ts"])
    op.create_index("ix_slack_indexed_items_item_type", "slack_indexed_items", ["item_type"])
    op.create_index("ix_slack_indexed_items_item_id", "slack_indexed_items", ["item_id"])

    op.create_table(
        "slack_visibility_cache",
        sa.Column("cache_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.String(length=255), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("can_access", sa.Boolean(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "team_id", "channel_id", name="uq_slack_visibility_cache"),
    )
    op.create_index("ix_slack_visibility_cache_user_id", "slack_visibility_cache", ["user_id"])
    op.create_index("ix_slack_visibility_cache_team_id", "slack_visibility_cache", ["team_id"])
    op.create_index("ix_slack_visibility_cache_channel_id", "slack_visibility_cache", ["channel_id"])
    op.create_index("ix_slack_visibility_cache_expires_at", "slack_visibility_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_slack_visibility_cache_expires_at", table_name="slack_visibility_cache")
    op.drop_index("ix_slack_visibility_cache_channel_id", table_name="slack_visibility_cache")
    op.drop_index("ix_slack_visibility_cache_team_id", table_name="slack_visibility_cache")
    op.drop_index("ix_slack_visibility_cache_user_id", table_name="slack_visibility_cache")
    op.drop_table("slack_visibility_cache")

    op.drop_index("ix_slack_indexed_items_item_id", table_name="slack_indexed_items")
    op.drop_index("ix_slack_indexed_items_item_type", table_name="slack_indexed_items")
    op.drop_index("ix_slack_indexed_items_thread_ts", table_name="slack_indexed_items")
    op.drop_index("ix_slack_indexed_items_message_ts", table_name="slack_indexed_items")
    op.drop_index("ix_slack_indexed_items_channel_id", table_name="slack_indexed_items")
    op.drop_index("ix_slack_indexed_items_team_id", table_name="slack_indexed_items")
    op.drop_index("ix_slack_indexed_items_workspace_id", table_name="slack_indexed_items")
    op.drop_index("ix_slack_indexed_items_source_id", table_name="slack_indexed_items")
    op.drop_table("slack_indexed_items")

    op.drop_index("ix_workspace_slack_sources_sync_owner_user_id", table_name="workspace_slack_sources")
    op.drop_index("ix_workspace_slack_sources_added_by_user_id", table_name="workspace_slack_sources")
    op.drop_index("ix_workspace_slack_sources_channel_id", table_name="workspace_slack_sources")
    op.drop_index("ix_workspace_slack_sources_team_id", table_name="workspace_slack_sources")
    op.drop_index("ix_workspace_slack_sources_workspace_id", table_name="workspace_slack_sources")
    op.drop_table("workspace_slack_sources")

    op.drop_index("ix_slack_user_connections_team_id", table_name="slack_user_connections")
    op.drop_index("ix_slack_user_connections_slack_user_id", table_name="slack_user_connections")
    op.drop_index("ix_slack_user_connections_user_id", table_name="slack_user_connections")
    op.drop_table("slack_user_connections")
