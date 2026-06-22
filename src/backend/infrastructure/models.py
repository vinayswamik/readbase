from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_key: Mapped[str] = mapped_column(
        String(320), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    session_token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rotated_from_session_id: Mapped[str | None] = mapped_column(
        String(96), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"

    bucket_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    window_start: Mapped[float] = mapped_column(Float, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AdminApproval(Base):
    """Legacy table from the old platform-admin login flow. Unused."""

    __tablename__ = "admin_approvals"

    approval_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_key: Mapped[str] = mapped_column(
        String(320), nullable=False, unique=True, index=True
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "name_key", name="uq_workspace_owner_name"),
    )

    workspace_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    name_key: Mapped[str] = mapped_column(String(80), nullable=False)
    join_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(96),
        ForeignKey("organizations.org_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        cascade="all, delete-orphan",
        back_populates="workspace",
    )
    invites: Mapped[list["WorkspaceInvite"]] = relationship(
        "WorkspaceInvite",
        cascade="all, delete-orphan",
        back_populates="workspace",
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "member_email_key", name="uq_workspace_member_email"
        ),
    )

    member_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=True, index=True
    )
    member_email: Mapped[str] = mapped_column(String(320), nullable=False)
    member_email_key: Mapped[str] = mapped_column(
        String(320), nullable=False, index=True
    )
    added_by_user_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    connector_manager: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="members")


class WorkspaceInvite(Base):
    __tablename__ = "workspace_invites"

    invite_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invitee_email: Mapped[str] = mapped_column(String(320), nullable=False)
    invitee_email_key: Mapped[str] = mapped_column(
        String(320), nullable=False, index=True
    )
    invitee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invitee_user_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=True, index=True
    )
    invitor_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    invitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invitor_designation: Mapped[str] = mapped_column(
        String(120), nullable=False, default=""
    )
    relation: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    node_display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_node_id: Mapped[str | None] = mapped_column(
        String(96),
        ForeignKey("hierarchy_nodes.node_id", ondelete="SET NULL"),
        nullable=True,
    )
    node_x: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    node_y: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    node_id: Mapped[str | None] = mapped_column(
        String(96),
        ForeignKey("hierarchy_nodes.node_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    join_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="invites")


class OrgSource(Base):
    __tablename__ = "org_sources"
    __table_args__ = (
        UniqueConstraint("org_id", "provider", "external_key", name="uq_org_source_identity"),
    )

    source_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    org_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_key: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    sync_owner_user_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=True, index=True
    )
    sync_status: Mapped[str] = mapped_column(String(32), default="idle", nullable=False)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class WorkspaceSourceSubscription(Base):
    __tablename__ = "workspace_source_subscriptions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_id", name="uq_workspace_source_subscription"),
    )

    subscription_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("org_sources.source_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_by_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class JiraUserConnection(Base):
    __tablename__ = "jira_user_connections"

    connection_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    atlassian_account_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    account_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class JiraUserSite(Base):
    __tablename__ = "jira_user_sites"
    __table_args__ = (
        UniqueConstraint("user_id", "cloud_id", name="uq_jira_user_site"),
    )

    site_row_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_url: Mapped[str] = mapped_column(String(500), nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class WorkspaceJiraSite(Base):
    __tablename__ = "workspace_jira_sites"

    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        primary_key=True,
    )
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_url: Mapped[str] = mapped_column(String(500), nullable=False)
    connected_by_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class WorkspaceJiraSource(Base):
    __tablename__ = "workspace_jira_sources"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "cloud_id", "project_id", name="uq_workspace_jira_project"
        ),
    )

    source_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_url: Mapped[str] = mapped_column(String(500), nullable=False)
    project_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    project_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    added_by_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    sync_owner_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    sync_status: Mapped[str] = mapped_column(String(32), default="idle", nullable=False)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class JiraIndexedItem(Base):
    __tablename__ = "jira_indexed_items"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "item_type", "item_id", name="uq_jira_indexed_item"
        ),
    )

    item_row_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    source_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspace_jira_sources.source_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    project_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    issue_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    issue_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    remote_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class JiraVisibilityCache(Base):
    __tablename__ = "jira_visibility_cache"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "cloud_id",
            "issue_id",
            "item_type",
            "item_id",
            name="uq_jira_visibility_cache",
        ),
    )

    cache_row_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cloud_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    issue_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    can_access: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class GithubUserConnection(Base):
    __tablename__ = "github_user_connections"

    connection_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    github_user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SlackUserConnection(Base):
    __tablename__ = "slack_user_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="uq_slack_user_connection_team"),
    )

    connection_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slack_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class WorkspaceSlackTeam(Base):
    __tablename__ = "workspace_slack_teams"
    __table_args__ = (
        UniqueConstraint("workspace_id", "team_id", name="uq_workspace_slack_team"),
    )

    team_link_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linked_by_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class WorkspaceSlackSource(Base):
    __tablename__ = "workspace_slack_sources"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "team_id", "channel_id", name="uq_workspace_slack_channel"
        ),
    )

    source_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_is_private: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    added_by_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    sync_owner_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    sync_status: Mapped[str] = mapped_column(String(32), default="idle", nullable=False)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_message_ts: Mapped[str | None] = mapped_column(String(64), nullable=True)
    next_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SlackIndexedItem(Base):
    __tablename__ = "slack_indexed_items"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "item_type", "item_id", name="uq_slack_indexed_item"
        ),
    )

    item_row_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    source_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspace_slack_sources.source_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    message_ts: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    thread_ts: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    remote_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class SlackVisibilityCache(Base):
    __tablename__ = "slack_visibility_cache"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "team_id", "channel_id", name="uq_slack_visibility_cache"
        ),
    )

    cache_row_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    can_access: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class WorkspaceSlackAccessCache(Base):
    __tablename__ = "workspace_slack_access_cache"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            "team_id",
            "channel_id",
            name="uq_workspace_slack_access_cache",
        ),
    )

    cache_row_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    can_access: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class HierarchyNode(Base):
    __tablename__ = "hierarchy_nodes"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "assigned_user_id", name="uq_hierarchy_node_assigned_user"
        ),
    )

    node_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    assigned_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    x: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    y: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class HierarchyConnection(Base):
    __tablename__ = "hierarchy_connections"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "parent_node_id",
            "child_node_id",
            name="uq_hierarchy_connection",
        ),
        UniqueConstraint(
            "workspace_id", "child_node_id", name="uq_hierarchy_child_parent"
        ),
    )

    connection_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_node_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("hierarchy_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_node_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("hierarchy_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


from src.backend.infrastructure.storage_models import (  # noqa: E402,F401
    Organization,
    OrganizationMember,
    OrganizationStorageConfig,
)

from src.backend.infrastructure.connector_models import (  # noqa: E402,F401
    BitbucketUserConnection,
    ConfluenceIndexedItem,
    ConfluenceUserConnection,
    ConfluenceUserSite,
    ConfluenceVisibilityCache,
    GitlabUserConnection,
    LinearIndexedItem,
    LinearUserConnection,
    LinearVisibilityCache,
    NotionIndexedItem,
    NotionUserConnection,
    NotionVisibilityCache,
    TeamsUserConnection,
    WorkspaceConfluenceSource,
    WorkspaceLinearSource,
    WorkspaceNotionSource,
)
