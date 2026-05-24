import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.backend.application.services import slack_service, workspace_service
from src.backend.application.services.slack.normalize import normalize_messages
from src.backend.infrastructure import database
from src.backend.infrastructure.models import SlackUserConnection


class SlackServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database(seed_admins=False)

    def tearDown(self):
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_add_slack_source_requires_workspace_access_and_slack_channel_access(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        workspace_service.add_workspace_member("admin-1", workspace["workspace_id"], "member@example.com")
        self._connect_slack_user("member-1")

        with self.assertRaises(Exception):
            slack_service.add_workspace_slack_source(
                workspace["workspace_id"],
                "other-1",
                "other@example.com",
                self._channel_payload(),
            )

        with patch("src.backend.application.services.slack.sources.verify_slack_channel_access", return_value=True):
            source = slack_service.add_workspace_slack_source(
                workspace["workspace_id"],
                "member-1",
                "member@example.com",
                self._channel_payload(),
            )

        self.assertEqual(source["channel_name"], "engineering")
        self.assertEqual(source["sync_owner_user_id"], "member-1")

    def test_permission_gate_excludes_unconnected_user_slack_matches(self):
        matches = [
            {
                "source_type": "slack",
                "team_id": "T1",
                "channel_id": "C1",
                "text": "hidden",
            },
            {"source_type": "repo", "text": "visible"},
        ]

        filtered = slack_service.filter_slack_matches_for_user("member-1", matches)

        self.assertEqual(filtered, [{"source_type": "repo", "text": "visible"}])

    def test_permission_gate_uses_live_verification_before_allowing_match(self):
        self._connect_slack_user("member-1")
        match = {
            "source_type": "slack",
            "team_id": "T1",
            "channel_id": "C1",
            "text": "visible",
        }

        with patch("src.backend.application.services.slack.permissions.verify_slack_channel_access", return_value=True) as verify:
            filtered = slack_service.filter_slack_matches_for_user("member-1", [match])

        self.assertEqual(filtered, [match])
        verify.assert_called_once()

    def test_list_visible_slack_channels_returns_suggestions(self):
        self._connect_slack_user("member-1")
        payload = {
            "ok": True,
            "channels": [
                {"id": "C1", "name": "engineering", "is_private": False},
                {"id": "C2", "name": "sales", "is_private": True},
            ],
            "response_metadata": {"next_cursor": ""},
        }

        with patch("src.backend.application.services.slack.sources.slack_api_request", return_value=payload):
            channels = slack_service.list_visible_slack_channels("member-1", "T1", query="eng")

        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["channel_name"], "engineering")
        self.assertEqual(channels[0]["team_id"], "T1")

    def test_normalize_messages_creates_slack_metadata(self):
        source = {
            "source_id": "slack-1",
            "workspace_id": "workspace-1",
            "team_id": "T1",
            "team_name": "Acme",
            "team_domain": "acme",
            "channel_id": "C1",
            "channel_name": "engineering",
        }

        items = normalize_messages(source, [{"ts": "1710000000.000100", "user": "U1", "text": "Ship <https://x.test|the release>"}])

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["item_type"], "message")
        self.assertIn("the release", items[0]["body"])
        self.assertEqual(items[0]["source_url"], "https://acme.slack.com/archives/C1/p1710000000000100")

    def _connect_slack_user(self, user_id: str) -> None:
        with database.session_scope() as session:
            session.add(
                SlackUserConnection(
                    user_id=user_id,
                    slack_user_id="U1",
                    team_id="T1",
                    team_name="Acme",
                    team_domain="acme",
                    access_token_encrypted=slack_service._encrypt_token("xoxp-token"),
                    scopes="channels:read,groups:read,channels:history,groups:history",
                )
            )

    def _channel_payload(self) -> dict:
        return {
            "team_id": "T1",
            "team_name": "Acme",
            "team_domain": "acme",
            "channel_id": "C1",
            "channel_name": "engineering",
            "is_private": False,
        }


if __name__ == "__main__":
    unittest.main()
