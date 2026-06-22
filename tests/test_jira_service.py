import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from src.backend.application.services import jira_service, workspace_service
from src.backend.infrastructure import database
from src.backend.infrastructure.models import JiraUserConnection, JiraUserSite, utc_now


class JiraServiceTests(unittest.TestCase):
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

    def test_add_jira_source_requires_connector_manager(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        workspace_service.add_workspace_member("admin-1", workspace["workspace_id"], "member@example.com")
        self._connect_jira_user("member-1")

        with self.assertRaises(Exception):
            jira_service.add_workspace_jira_source(
                workspace["workspace_id"],
                "member-1",
                "member@example.com",
                self._project_payload(),
            )

        workspace_service.update_workspace_member_connector_manager(
            "admin-1",
            workspace["workspace_id"],
            "member@example.com",
            True,
        )
        jira_service.connect_workspace_jira_site(
            workspace["workspace_id"],
            "member-1",
            "member@example.com",
            "cloud-1",
        )
        source = jira_service.add_workspace_jira_source(
            workspace["workspace_id"],
            "member-1",
            "member@example.com",
            self._project_payload(),
        )

        self.assertEqual(source["project_key"], "ENG")
        self.assertEqual(source["sync_owner_user_id"], "member-1")

    def test_permission_gate_excludes_unconnected_user_jira_matches(self):
        matches = [
            {
                "source_type": "jira",
                "cloud_id": "cloud-1",
                "issue_id": "10001",
                "item_type": "issue",
                "item_id": "10001",
                "text": "hidden",
            },
            {"source_type": "repo", "text": "visible"},
        ]

        filtered = jira_service.filter_jira_matches_for_user("member-1", matches)

        self.assertEqual(filtered, [{"source_type": "repo", "text": "visible"}])

    def test_permission_gate_uses_live_verification_before_allowing_match(self):
        self._connect_jira_user("member-1")
        match = {
            "source_type": "jira",
            "cloud_id": "cloud-1",
            "issue_id": "10001",
            "item_type": "issue",
            "item_id": "10001",
            "text": "visible",
        }

        with patch("src.backend.application.services.jira.permissions.verify_jira_item_access", return_value=True) as verify:
            filtered = jira_service.filter_jira_matches_for_user("member-1", [match])

        self.assertEqual(filtered, [match])
        verify.assert_called_once()

    def _connect_jira_user(self, user_id: str) -> None:
        with database.session_scope() as session:
            session.add(
                JiraUserConnection(
                    user_id=user_id,
                    atlassian_account_id=f"atl-{user_id}",
                    access_token_encrypted=jira_service._encrypt_token("access"),
                    refresh_token_encrypted=jira_service._encrypt_token("refresh"),
                    scopes="read:jira-work",
                    expires_at=utc_now() + timedelta(hours=1),
                )
            )
            session.add(
                JiraUserSite(
                    user_id=user_id,
                    cloud_id="cloud-1",
                    site_name="Acme",
                    site_url="https://acme.atlassian.net",
                    scopes="read:jira-work",
                )
            )

    def _project_payload(self) -> dict:
        return {
            "cloud_id": "cloud-1",
            "site_name": "Acme",
            "site_url": "https://acme.atlassian.net",
            "project_id": "10000",
            "project_key": "ENG",
            "project_name": "Engineering",
        }


if __name__ == "__main__":
    unittest.main()
