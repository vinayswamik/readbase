from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_key: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class AdminApproval(Base):
    __tablename__ = "admin_approvals"

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_key: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("owner_user_id", "name_key", name="uq_workspace_owner_name"),)

    workspace_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    name_key: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        cascade="all, delete-orphan",
        back_populates="workspace",
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "member_email_key", name="uq_workspace_member_email"),
    )

    member_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=True, index=True)
    member_email: Mapped[str] = mapped_column(String(320), nullable=False)
    member_email_key: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    added_by_user_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="members")


class WorkspaceConnector(Base):
    __tablename__ = "workspace_connectors"
    __table_args__ = (
        UniqueConstraint("workspace_id", "connector_id", name="uq_workspace_connector"),
    )

    connector_row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class HierarchyNode(Base):
    __tablename__ = "hierarchy_nodes"
    __table_args__ = (
        UniqueConstraint("workspace_id", "assigned_user_id", name="uq_hierarchy_node_assigned_user"),
    )

    node_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    assigned_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    x: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    y: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class HierarchyConnection(Base):
    __tablename__ = "hierarchy_connections"
    __table_args__ = (
        UniqueConstraint("workspace_id", "parent_node_id", "child_node_id", name="uq_hierarchy_connection"),
        UniqueConstraint("workspace_id", "child_node_id", name="uq_hierarchy_child_parent"),
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
    created_by_user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
