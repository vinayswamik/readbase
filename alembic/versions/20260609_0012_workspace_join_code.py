"""workspace join code for self-serve membership

Revision ID: 20260609_0012
Revises: 20260603_0011
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260609_0012"
down_revision = "20260603_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.add_column(sa.Column("join_code", sa.String(length=32), nullable=True))
        batch_op.create_index("ix_workspaces_join_code", ["join_code"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.drop_index("ix_workspaces_join_code")
        batch_op.drop_column("join_code")
