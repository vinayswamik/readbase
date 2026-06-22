"""workspace invite join link token

Revision ID: 20260609_0014
Revises: 20260609_0013
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260609_0014"
down_revision = "20260609_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workspace_invites", schema=None) as batch_op:
        batch_op.add_column(sa.Column("join_token", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_workspace_invites_join_token", ["join_token"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("workspace_invites", schema=None) as batch_op:
        batch_op.drop_index("ix_workspace_invites_join_token")
        batch_op.drop_column("join_token")
