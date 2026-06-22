from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.infrastructure.database import Base
from src.backend.infrastructure.models import utc_now


class Organization(Base):
    __tablename__ = "organizations"

    org_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    storage_config: Mapped["OrganizationStorageConfig | None"] = relationship(
        "OrganizationStorageConfig",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )


class OrganizationStorageConfig(Base):
    __tablename__ = "organization_storage_configs"

    org_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        primary_key=True,
    )
    blob_backend: Mapped[str] = mapped_column(String(32), default="local", nullable=False)
    storage_root: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    organization: Mapped[Organization] = relationship("Organization", back_populates="storage_config")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_organization_member"),)

    member_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
