from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.infrastructure.database import Base
from src.backend.infrastructure.models import utc_now


class BitbucketUserConnection(Base):
    __tablename__ = "bitbucket_user_connections"

    connection_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    bitbucket_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class GitlabUserConnection(Base):
    __tablename__ = "gitlab_user_connections"

    connection_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    gitlab_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class LinearUserConnection(Base):
    __tablename__ = "linear_user_connections"

    connection_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    linear_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    workspace_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class WorkspaceLinearSource(Base):
    __tablename__ = "workspace_linear_sources"
    __table_args__ = (
        UniqueConstraint("workspace_id", "linear_team_id", "linear_project_id", name="uq_workspace_linear_source"),
    )

    source_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(96), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True)
    linear_team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    linear_project_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    sync_owner_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    sync_status: Mapped[str] = mapped_column(String(32), default="idle", nullable=False)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class LinearIndexedItem(Base):
    __tablename__ = "linear_indexed_items"
    __table_args__ = (
        UniqueConstraint("source_id", "item_type", "item_id", name="uq_linear_indexed_item"),
    )

    item_row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(96), ForeignKey("workspace_linear_sources.source_id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    linear_team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    linear_project_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    issue_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    issue_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    remote_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LinearVisibilityCache(Base):
    __tablename__ = "linear_visibility_cache"
    __table_args__ = (
        UniqueConstraint("user_id", "issue_id", "item_type", "item_id", name="uq_linear_visibility_cache"),
    )

    cache_row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    issue_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    can_access: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ConfluenceUserConnection(Base):
    __tablename__ = "confluence_user_connections"

    connection_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    atlassian_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    account_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ConfluenceUserSite(Base):
    __tablename__ = "confluence_user_sites"
    __table_args__ = (
        UniqueConstraint("user_id", "cloud_id", name="uq_confluence_user_site"),
    )

    site_row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_url: Mapped[str] = mapped_column(String(500), nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class WorkspaceConfluenceSource(Base):
    __tablename__ = "workspace_confluence_sources"
    __table_args__ = (
        UniqueConstraint("workspace_id", "cloud_id", "space_id", name="uq_workspace_confluence_space"),
    )

    source_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(96), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True)
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_url: Mapped[str] = mapped_column(String(500), nullable=False)
    space_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    space_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    space_name: Mapped[str] = mapped_column(String(255), nullable=False)
    added_by_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    sync_owner_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    sync_status: Mapped[str] = mapped_column(String(32), default="idle", nullable=False)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ConfluenceIndexedItem(Base):
    __tablename__ = "confluence_indexed_items"
    __table_args__ = (
        UniqueConstraint("source_id", "item_type", "item_id", name="uq_confluence_indexed_item"),
    )

    item_row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(96), ForeignKey("workspace_confluence_sources.source_id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    space_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    space_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    remote_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ConfluenceVisibilityCache(Base):
    __tablename__ = "confluence_visibility_cache"
    __table_args__ = (
        UniqueConstraint("user_id", "cloud_id", "page_id", name="uq_confluence_visibility_cache"),
    )

    cache_row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    page_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    can_access: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
