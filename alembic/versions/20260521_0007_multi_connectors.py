"""multi connector expansion

Revision ID: 20260521_0007
Revises: 20260520_0006
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260521_0007"
down_revision = "20260520_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_bitbucket()
    create_gitlab()
    create_linear()
    create_confluence()


def downgrade() -> None:
    for table in (
        "confluence_visibility_cache",
        "confluence_indexed_items",
        "workspace_confluence_sources",
        "confluence_user_sites",
        "confluence_user_connections",
        "linear_visibility_cache",
        "linear_indexed_items",
        "workspace_linear_sources",
        "linear_user_connections",
        "gitlab_user_connections",
        "bitbucket_user_connections",
    ):
        op.drop_table(table)


def create_bitbucket() -> None:
    op.create_table(
        "bitbucket_user_connections",
        sa.Column("connection_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("bitbucket_account_id", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(1000), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def create_gitlab() -> None:
    op.create_table(
        "gitlab_user_connections",
        sa.Column("connection_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("gitlab_user_id", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(1000), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def create_linear() -> None:
    op.create_table(
        "linear_user_connections",
        sa.Column("connection_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("linear_user_id", sa.String(255), nullable=True),
        sa.Column("workspace_id", sa.String(255), nullable=True),
        sa.Column("workspace_name", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "workspace_linear_sources",
        sa.Column("source_id", sa.String(96), primary_key=True),
        sa.Column("workspace_id", sa.String(96), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
        sa.Column("linear_team_id", sa.String(255), nullable=False),
        sa.Column("team_name", sa.String(255), nullable=False),
        sa.Column("linear_project_id", sa.String(255), nullable=True),
        sa.Column("project_name", sa.String(255), nullable=True),
        sa.Column("added_by_user_id", sa.String(255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_owner_user_id", sa.String(255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_status", sa.String(32), nullable=False, server_default="idle"),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "linear_team_id", "linear_project_id", name="uq_workspace_linear_source"),
    )
    create_indexed_and_cache("linear")


def create_confluence() -> None:
    op.create_table(
        "confluence_user_connections",
        sa.Column("connection_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("atlassian_account_id", sa.String(255), nullable=True),
        sa.Column("account_email", sa.String(320), nullable=True),
        sa.Column("account_name", sa.String(255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "confluence_user_sites",
        sa.Column("site_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("cloud_id", sa.String(255), nullable=False),
        sa.Column("site_name", sa.String(255), nullable=False),
        sa.Column("site_url", sa.String(500), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.String(1000), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "cloud_id", name="uq_confluence_user_site"),
    )
    op.create_table(
        "workspace_confluence_sources",
        sa.Column("source_id", sa.String(96), primary_key=True),
        sa.Column("workspace_id", sa.String(96), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
        sa.Column("cloud_id", sa.String(255), nullable=False),
        sa.Column("site_name", sa.String(255), nullable=False),
        sa.Column("site_url", sa.String(500), nullable=False),
        sa.Column("space_id", sa.String(96), nullable=False),
        sa.Column("space_key", sa.String(64), nullable=False),
        sa.Column("space_name", sa.String(255), nullable=False),
        sa.Column("added_by_user_id", sa.String(255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_owner_user_id", sa.String(255), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("sync_status", sa.String(32), nullable=False, server_default="idle"),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "cloud_id", "space_id", name="uq_workspace_confluence_space"),
    )
    create_indexed_and_cache("confluence")


def create_indexed_and_cache(prefix: str) -> None:
    issue_columns = []
    if prefix == "linear":
        issue_columns = [sa.Column("linear_team_id", sa.String(255), nullable=False), sa.Column("linear_project_id", sa.String(255), nullable=True), sa.Column("issue_id", sa.String(255), nullable=False), sa.Column("issue_key", sa.String(64), nullable=False)]
    else:
        issue_columns = [sa.Column("cloud_id", sa.String(255), nullable=False), sa.Column("space_id", sa.String(96), nullable=False), sa.Column("space_key", sa.String(64), nullable=False), sa.Column("page_id", sa.String(96), nullable=False)]
    source_table = "workspace_linear_sources" if prefix == "linear" else "workspace_confluence_sources"
    op.create_table(
        f"{prefix}_indexed_items",
        sa.Column("item_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(96), sa.ForeignKey(f"{source_table}.source_id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.String(96), nullable=False),
        *issue_columns,
        sa.Column("item_type", sa.String(32), nullable=False),
        sa.Column("item_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("remote_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "item_type", "item_id", name=f"uq_{prefix}_indexed_item"),
    )
    cache_columns = [sa.Column("issue_id", sa.String(255), nullable=False), sa.Column("item_type", sa.String(32), nullable=False), sa.Column("item_id", sa.String(255), nullable=False)] if prefix == "linear" else [sa.Column("cloud_id", sa.String(255), nullable=False), sa.Column("page_id", sa.String(96), nullable=False)]
    op.create_table(
        f"{prefix}_visibility_cache",
        sa.Column("cache_row_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        *cache_columns,
        sa.Column("can_access", sa.Boolean(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
