import tempfile
import unittest
from pathlib import Path

from sqlalchemy import inspect, text

from src.backend.infrastructure import database


class DatabaseSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")

    def tearDown(self):
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_init_database_adds_workspace_invite_expires_at_to_existing_table(self):
        with database.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE workspace_invites (
                        invite_id VARCHAR(96) NOT NULL PRIMARY KEY,
                        workspace_id VARCHAR(96) NOT NULL,
                        invitee_email VARCHAR(320) NOT NULL,
                        invitee_email_key VARCHAR(320) NOT NULL,
                        invitee_name VARCHAR(255) NOT NULL,
                        invitee_user_id VARCHAR(255),
                        invitor_user_id VARCHAR(255) NOT NULL,
                        invitor_name VARCHAR(255) NOT NULL,
                        invitor_designation VARCHAR(120) NOT NULL DEFAULT '',
                        relation VARCHAR(120) NOT NULL,
                        reason TEXT NOT NULL,
                        node_display_name VARCHAR(120) NOT NULL,
                        parent_node_id VARCHAR(96),
                        node_x FLOAT NOT NULL DEFAULT 0,
                        node_y FLOAT NOT NULL DEFAULT 0,
                        node_id VARCHAR(96),
                        status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        join_token VARCHAR(64),
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO workspace_invites (
                        invite_id,
                        workspace_id,
                        invitee_email,
                        invitee_email_key,
                        invitee_name,
                        invitor_user_id,
                        invitor_name,
                        relation,
                        reason,
                        node_display_name,
                        created_at
                    )
                    VALUES (
                        'invite-1',
                        'workspace-1',
                        'member@example.com',
                        'member@example.com',
                        'Member',
                        'owner-1',
                        'Owner',
                        'Peer',
                        'Needs access',
                        'Member',
                        '2026-06-18 12:00:00'
                    )
                    """
                )
            )

        database.init_database()

        columns = {
            column["name"]
            for column in inspect(database.engine).get_columns("workspace_invites")
        }
        self.assertIn("expires_at", columns)

        with database.engine.connect() as connection:
            expires_at = connection.execute(
                text("SELECT expires_at FROM workspace_invites WHERE invite_id = 'invite-1'")
            ).scalar_one()

        self.assertEqual(expires_at, "2026-06-25 12:00:00")


if __name__ == "__main__":
    unittest.main()
