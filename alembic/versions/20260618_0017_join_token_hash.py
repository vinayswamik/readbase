"""Hash workspace invite join tokens at rest."""

from __future__ import annotations

import hashlib

from alembic import op
import sqlalchemy as sa

revision = "20260618_0017"
down_revision = "20260618_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT invite_id, join_token FROM workspace_invites WHERE join_token IS NOT NULL")
    ).fetchall()
    for invite_id, join_token in rows:
        if not join_token or len(join_token) == 64:
            continue
        hashed = hashlib.sha256(join_token.encode("utf-8")).hexdigest()
        connection.execute(
            sa.text(
                "UPDATE workspace_invites "
                "SET join_token = :hashed, invitee_email_key = :email_key "
                "WHERE invite_id = :invite_id"
            ),
            {
                "hashed": hashed,
                "email_key": f"link:{hashed}",
                "invite_id": invite_id,
            },
        )


def downgrade() -> None:
    pass
