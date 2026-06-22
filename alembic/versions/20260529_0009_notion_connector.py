"""notion connector

Revision ID: 20260529_0009
Revises: 20260526_0008
Create Date: 2026-05-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260529_0009"
down_revision = "20260526_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notion_user_connections",
        sa.Column("connection_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("notion_workspace_id", sa.String(255), nullable=True),
        sa.Column("workspace_name", sa.String(255), nullable=True),
        sa.Column("workspace_icon", sa.String(1000), nullable=True),
        sa.Column("bot_id", sa.String(255), nullable=True),
        sa.Column("owner_type", sa.String(32), nullable=True),
        sa.Column("owner_name", sa.String(255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "workspace_notion_sources",
        sa.Column("source_id", sa.String(96), primary_key=True),
        sa.Column("workspace_id", sa.String(96), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
        sa.Column("notion_workspace_id", sa.String(255), nullable=False),
        sa.Column("database_id", sa.String(96), nullable=False),
        sa.Column("database_title", sa.String(255), nullable=False),
        sa.Column("added_by_user_id", sa.String(255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_owner_user_id", sa.String(255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_status", sa.String(32), nullable=False, server_default="idle"),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "database_id", name="uq_workspace_notion_database"),
    )
    op.create_table(
        "notion_indexed_items",
        sa.Column("item_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(96), sa.ForeignKey("workspace_notion_sources.source_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.String(96), nullable=False),
        sa.Column("notion_workspace_id", sa.String(255), nullable=False),
        sa.Column("database_id", sa.String(96), nullable=False),
        sa.Column("page_id", sa.String(96), nullable=False),
        sa.Column("item_type", sa.String(32), nullable=False),
        sa.Column("item_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("remote_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "item_type", "item_id", name="uq_notion_indexed_item"),
    )
    op.create_table(
        "notion_visibility_cache",
        sa.Column("cache_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", sa.String(96), nullable=False),
        sa.Column("can_access", sa.Boolean(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "page_id", name="uq_notion_visibility_cache"),
    )


def downgrade() -> None:
    for table in (
        "notion_visibility_cache",
        "notion_indexed_items",
        "workspace_notion_sources",
        "notion_user_connections",
    ):
        op.drop_table(table)
