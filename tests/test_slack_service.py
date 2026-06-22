import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select

from src.backend.application.services import slack_service, workspace_service
from src.backend.application.services.exceptions import ValidationError
from src.backend.application.services.slack.auth import slack_callback_url
from src.backend.application.services.question_service import ask_repository_question
from src.backend.application.services.slack.normalize import normalize_messages
from src.backend.infrastructure import database
from src.backend.infrastructure.models import SlackUserConnection, User, WorkspaceSlackAccessCache, utc_now


class SlackServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database()

    def tearDown(self):
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_add_slack_source_requires_linked_team(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        self._ensure_user("admin-1", "admin@example.com")
        self._connect_slack_user("admin-1")

        with patch("src.backend.application.services.slack.sources.verify_slack_channel_access", return_value=True):
            with self.assertRaises(Exception):
                slack_service.add_workspace_slack_source(
                    workspace["workspace_id"],
                    "admin-1",
                    "admin@example.com",
                    self._channel_payload(),
                )

    def test_add_slack_source_requires_workspace_access_and_slack_channel_access(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        self._ensure_user("admin-1", "admin@example.com")
        self._connect_slack_user("admin-1")
        self._link_slack_team(workspace["workspace_id"], "admin-1")

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
                "admin-1",
                "admin@example.com",
                self._channel_payload(),
            )

        self.assertEqual(source["channel_name"], "engineering")
        self.assertEqual(source["sync_owner_user_id"], "admin-1")

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

    def test_permission_gate_scopes_matches_to_workspace_channel_set(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        self._ensure_user("admin-1", "admin@example.com")
        self._connect_slack_user("admin-1")
        self._link_slack_team(workspace["workspace_id"], "admin-1")
        with patch("src.backend.application.services.slack.sources.verify_slack_channel_access", return_value=True):
            slack_service.add_workspace_slack_source(
                workspace["workspace_id"],
                "admin-1",
                "admin@example.com",
                self._channel_payload(),
            )
        matches = [
            {"source_type": "slack", "team_id": "T1", "channel_id": "C1", "text": "allowed"},
            {"source_type": "slack", "team_id": "T1", "channel_id": "C2", "text": "blocked"},
        ]

        with patch("src.backend.application.services.slack.permissions.verify_slack_channel_access", return_value=True):
            filtered = slack_service.filter_slack_matches_for_user("admin-1", matches, workspace_id=workspace["workspace_id"])

        self.assertEqual(filtered, [{"source_type": "slack", "team_id": "T1", "channel_id": "C1", "text": "allowed"}])

    def test_question_flow_filters_permissions_before_top_k_cutoff(self):
        with (
            patch("src.backend.application.services.question_service.list_repositories", return_value=[]),
            patch("src.backend.application.services.question_service.search_jira", return_value=[]),
            patch(
                "src.backend.application.services.question_service.search_slack",
                return_value=[
                    {"source_type": "slack", "team_id": "T1", "channel_id": "C1", "score": 0.99, "text": "blocked"},
                    {"source_type": "slack", "team_id": "T1", "channel_id": "C2", "score": 0.70, "text": "allowed"},
                ],
            ),
            patch("src.backend.application.services.question_service.search_linear", return_value=[]),
            patch("src.backend.application.services.question_service.search_confluence", return_value=[]),
            patch("src.backend.application.services.question_service.search_notion", return_value=[]),
            patch("src.backend.application.services.question_service.filter_repo_matches_for_user", side_effect=lambda _uid, m: m),
            patch("src.backend.application.services.question_service.filter_jira_matches_for_user", side_effect=lambda _uid, m: m),
            patch(
                "src.backend.application.services.question_service.filter_slack_matches_for_user",
                return_value=[{"source_type": "slack", "team_id": "T1", "channel_id": "C2", "score": 0.70, "text": "allowed"}],
            ) as filter_slack,
            patch("src.backend.application.services.question_service.filter_linear_matches_for_user", side_effect=lambda _uid, m: m),
            patch("src.backend.application.services.question_service.filter_confluence_matches_for_user", side_effect=lambda _uid, m: m),
            patch("src.backend.application.services.question_service.filter_notion_matches_for_user", side_effect=lambda _uid, m: m),
            patch(
                "src.backend.application.services.question_service.answer_question",
                return_value={"answer": "ok", "mode": "grounded", "sources": [{"id": "allowed"}]},
            ) as answerer,
        ):
            ask_repository_question(
                repo_id=None,
                workspace_id="workspace-1",
                user_id="member-1",
                question="what changed?",
                top_k=1,
            )

        filter_slack.assert_called_once()
        answer_sources = answerer.call_args[0][1]
        self.assertEqual(len(answer_sources), 1)
        self.assertEqual(answer_sources[0]["channel_id"], "C2")

    def test_workspace_access_cache_short_circuits_live_permission_check(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        self._ensure_user("admin-1", "admin@example.com")
        self._connect_slack_user("admin-1")
        self._link_slack_team(workspace["workspace_id"], "admin-1")
        with patch("src.backend.application.services.slack.sources.verify_slack_channel_access", return_value=True):
            slack_service.add_workspace_slack_source(
                workspace["workspace_id"],
                "admin-1",
                "admin@example.com",
                self._channel_payload(),
            )
        with database.session_scope() as session:
            session.add(
                WorkspaceSlackAccessCache(
                    workspace_id=workspace["workspace_id"],
                    user_id="admin-1",
                    team_id="T1",
                    channel_id="C1",
                    can_access=True,
                    checked_at=utc_now(),
                    expires_at=utc_now() + timedelta(minutes=5),
                )
            )
        matches = [{"source_type": "slack", "team_id": "T1", "channel_id": "C1", "text": "visible"}]
        with (
            patch(
                "src.backend.application.services.slack.permissions.read_workspace_access_cache_map",
                return_value={("T1", "C1"): True},
            ),
            patch("src.backend.application.services.slack.permissions.can_user_access_slack_channel") as live_check,
        ):
            filtered = slack_service.filter_slack_matches_for_user("admin-1", matches, workspace_id=workspace["workspace_id"])

        self.assertEqual(filtered, matches)
        live_check.assert_not_called()

    def test_list_workspace_slack_channels_scopes_to_linked_teams(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        self._ensure_user("admin-1", "admin@example.com")
        self._connect_slack_user("admin-1")
        self._link_slack_team(workspace["workspace_id"], "admin-1")
        payload = {
            "ok": True,
            "channels": [{"id": "C1", "name": "engineering", "is_private": False}],
            "response_metadata": {"next_cursor": ""},
        }

        with patch("src.backend.application.services.slack.sources.slack_api_request", return_value=payload):
            channels = slack_service.list_workspace_slack_channels(workspace["workspace_id"], "admin-1", query="eng")

        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["channel_name"], "engineering")

    def test_list_workspace_slack_channels_returns_all_without_query(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        self._ensure_user("admin-1", "admin@example.com")
        self._connect_slack_user("admin-1")
        self._link_slack_team(workspace["workspace_id"], "admin-1")
        payload = {
            "ok": True,
            "channels": [
                {"id": "C1", "name": "engineering", "is_private": False},
                {"id": "C2", "name": "sales", "is_private": False},
            ],
            "response_metadata": {"next_cursor": ""},
        }

        with patch("src.backend.application.services.slack.sources.slack_api_request", return_value=payload):
            channels = slack_service.list_workspace_slack_channels(workspace["workspace_id"], "admin-1", query="")

        self.assertEqual(len(channels), 2)
        self.assertEqual({channel["channel_name"] for channel in channels}, {"engineering", "sales"})

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

    def test_list_visible_slack_channels_matches_team_name(self):
        self._connect_slack_user("member-1")
        payload = {
            "ok": True,
            "channels": [
                {"id": "C1", "name": "general", "is_private": False},
                {"id": "C2", "name": "random", "is_private": False},
            ],
            "response_metadata": {"next_cursor": ""},
        }

        with patch("src.backend.application.services.slack.sources.slack_api_request", return_value=payload):
            channels = slack_service.list_visible_slack_channels("member-1", "T1", query="acme")

        self.assertEqual(len(channels), 2)

    def test_list_visible_slack_channels_ranks_prefix_matches_first(self):
        self._connect_slack_user("member-1")
        payload = {
            "ok": True,
            "channels": [
                {"id": "C1", "name": "team-eng", "is_private": False},
                {"id": "C2", "name": "engineering", "is_private": False},
            ],
            "response_metadata": {"next_cursor": ""},
        }

        with patch("src.backend.application.services.slack.sources.slack_api_request", return_value=payload):
            channels = slack_service.list_visible_slack_channels("member-1", "T1", query="eng")

        self.assertEqual([channel["channel_name"] for channel in channels], ["engineering", "team-eng"])

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

    def test_build_slack_authorize_url_uses_pkce(self):
        with patch.dict("os.environ", {"SLACK_CLIENT_ID": "123.456", "SLACK_CLIENT_SECRET": "secret"}):
            url = slack_service.build_slack_authorize_url("state-token", "verifier-token")
        self.assertIn("code_challenge=", url)
        self.assertIn("code_challenge_method=S256", url)
        self.assertIn("state=state-token", url)

    def test_slack_callback_url_defaults_to_app_base_url(self):
        env = {
            "APP_BASE_URL": "http://127.0.0.1:8000",
            "SLACK_REDIRECT_URI": "",
            "READBASE_SSL_CERTFILE": "",
        }
        with patch.dict("os.environ", env, clear=False):
            self.assertEqual(
                slack_callback_url(),
                "http://127.0.0.1:8000/api/me/integrations/slack/callback",
            )

    def test_slack_callback_url_auto_upgrades_when_local_ssl_configured(self):
        env = {
            "APP_BASE_URL": "http://127.0.0.1:8000",
            "READBASE_SSL_CERTFILE": "certs/readbase-local.pem",
            "SLACK_REDIRECT_URI": "",
        }
        with patch.dict("os.environ", env, clear=False):
            self.assertEqual(
                slack_callback_url(),
                "https://127.0.0.1:8000/api/me/integrations/slack/callback",
            )

    def test_slack_callback_url_rejects_https_without_local_ssl(self):
        env = {
            "APP_BASE_URL": "http://127.0.0.1:8000",
            "SLACK_REDIRECT_URI": "https://127.0.0.1:8000/api/me/integrations/slack/callback",
            "READBASE_SSL_CERTFILE": "",
        }
        with patch.dict("os.environ", env, clear=False):
            with self.assertRaises(ValidationError):
                slack_callback_url()

    def test_slack_callback_url_allows_external_https_tunnel(self):
        env = {
            "APP_BASE_URL": "http://127.0.0.1:8000",
            "SLACK_REDIRECT_URI": "https://example.ngrok.app/api/me/integrations/slack/callback",
            "READBASE_SSL_CERTFILE": "",
        }
        with patch.dict("os.environ", env, clear=False):
            self.assertEqual(
                slack_callback_url(),
                "https://example.ngrok.app/api/me/integrations/slack/callback",
            )

    def test_link_workspace_slack_team_rejects_duplicate(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        self._ensure_user("admin-1", "admin@example.com")
        self._connect_slack_user("admin-1")
        self._link_slack_team(workspace["workspace_id"], "admin-1")

        with self.assertRaises(Exception) as ctx:
            slack_service.link_workspace_slack_team(workspace["workspace_id"], "admin-1", "T1")

        self.assertIn("already connected", str(ctx.exception).lower())

    def test_exchange_slack_code_skips_when_workspace_already_linked(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        self._ensure_user("admin-1", "admin@example.com")
        self._connect_slack_user("admin-1")
        self._link_slack_team(workspace["workspace_id"], "admin-1")
        token_payload = {
            "authed_user": {
                "id": "U2",
                "access_token": "xoxp-new-token",
                "scope": "channels:read",
            },
            "team": {"id": "T1", "name": "Acme Updated"},
        }

        with (
            patch("src.backend.application.services.slack.auth.slack_oauth_request", return_value=token_payload),
            patch("src.backend.application.services.slack.auth.fetch_team_domain", return_value="acme-updated"),
        ):
            result = slack_service.exchange_slack_code_for_connection(
                "admin-1",
                "code-1",
                workspace_id=workspace["workspace_id"],
                code_verifier="verifier-1",
            )

        self.assertTrue(result.get("already_connected"))
        with database.session_scope() as session:
            connection = session.scalar(
                select(SlackUserConnection).where(
                    SlackUserConnection.user_id == "admin-1",
                    SlackUserConnection.team_id == "T1",
                )
            )
            self.assertEqual(connection.team_name, "Acme")

    def _ensure_user(self, user_id: str, email: str) -> None:
        with database.session_scope() as session:
            if session.get(User, user_id) is not None:
                return
            session.add(
                User(
                    user_id=user_id,
                    email=email,
                    email_key=email.strip().lower(),
                    name="Member",
                )
            )

    def _link_slack_team(self, workspace_id: str, user_id: str, team_id: str = "T1") -> None:
        slack_service.link_workspace_slack_team(workspace_id, user_id, team_id)

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
