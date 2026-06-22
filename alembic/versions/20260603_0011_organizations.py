"""organizations and workspace storage routing

Revision ID: 20260603_0011
Revises: 20260529_0010
Create Date: 2026-06-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260603_0011"
down_revision = "20260529_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("org_id", sa.String(length=96), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_key", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organizations_name_key", "organizations", ["name_key"], unique=True)

    op.create_table(
        "organization_storage_configs",
        sa.Column("org_id", sa.String(length=96), sa.ForeignKey("organizations.org_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("blob_backend", sa.String(length=32), nullable=False),
        sa.Column("storage_root", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "organization_members",
        sa.Column("member_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.String(length=96), sa.ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("org_id", "user_id", name="uq_organization_member"),
    )
    op.create_index("ix_organization_members_org_id", "organization_members", ["org_id"])
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])

    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.String(length=96), nullable=True))
        batch_op.create_foreign_key(
            "fk_workspaces_organization_id",
            "organizations",
            ["organization_id"],
            ["org_id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_workspaces_organization_id", ["organization_id"])


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.drop_index("ix_workspaces_organization_id")
        batch_op.drop_constraint("fk_workspaces_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")

    op.drop_table("organization_members")
    op.drop_table("organization_storage_configs")
    op.drop_table("organizations")
