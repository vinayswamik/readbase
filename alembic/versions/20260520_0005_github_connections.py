"""github connections

Revision ID: 20260520_0005
Revises: 20260520_0004
Create Date: 2026-05-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260520_0005"
down_revision = "20260520_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_user_connections",
        sa.Column("connection_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("github_user_id", sa.String(length=255), nullable=True),
        sa.Column("login", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=1000), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_github_user_connection_user_id"),
    )
    op.create_index("ix_github_user_connections_user_id", "github_user_connections", ["user_id"])
    op.create_index("ix_github_user_connections_github_user_id", "github_user_connections", ["github_user_id"])


def downgrade() -> None:
    op.drop_index("ix_github_user_connections_github_user_id", table_name="github_user_connections")
    op.drop_index("ix_github_user_connections_user_id", table_name="github_user_connections")
    op.drop_table("github_user_connections")
