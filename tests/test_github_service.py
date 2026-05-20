import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.backend.application.services import github_service, repo_service, workspace_service
from src.backend.infrastructure import database
from src.backend.infrastructure.models import GithubUserConnection
from src.backend.application.services.jira.crypto import encrypt_token


class GithubServiceTests(unittest.TestCase):
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

    def test_repo_filter_excludes_github_without_connection(self):
        matches = [
            {"source_type": "repo", "repo_url": "https://github.com/acme/private", "text": "hidden"},
            {"source_type": "jira", "text": "jira"},
        ]

        filtered = github_service.filter_repo_matches_for_user("member-1", matches)

        self.assertEqual(filtered, [{"source_type": "jira", "text": "jira"}])

    def test_repo_filter_allows_verified_github_repo(self):
        self._connect_github_user("member-1")
        match = {"source_type": "repo", "repo_url": "https://github.com/acme/private", "text": "visible"}

        with patch("src.backend.application.services.github.permissions.github_json_request", return_value={"id": 1}):
            filtered = github_service.filter_repo_matches_for_user("member-1", [match])

        self.assertEqual(filtered, [match])

    def test_list_visible_github_repositories_returns_suggestions(self):
        self._connect_github_user("member-1")
        payload = [
            {
                "id": 1,
                "name": "private",
                "full_name": "acme/private",
                "html_url": "https://github.com/acme/private",
                "private": True,
                "description": "Backend repo",
                "owner": {"login": "acme"},
                "updated_at": "2026-05-20T00:00:00Z",
            },
            {
                "id": 2,
                "name": "website",
                "full_name": "acme/website",
                "html_url": "https://github.com/acme/website",
                "private": False,
                "owner": {"login": "acme"},
            },
        ]

        with patch("src.backend.application.services.github.repos.github_json_request", return_value=payload):
            repositories = github_service.list_visible_github_repositories("member-1", query="priv")

        self.assertEqual(len(repositories), 1)
        self.assertEqual(repositories[0]["full_name"], "acme/private")
        self.assertEqual(repositories[0]["html_url"], "https://github.com/acme/private")

    def test_index_repository_requires_connected_github_user(self):
        with self.assertRaises(Exception):
            repo_service.index_repository(
                "https://github.com/acme/private",
                user_id="member-1",
                user_email="member@example.com",
            )

    def test_index_repository_requires_connector_manager_and_github_access(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        workspace_service.add_workspace_member("admin-1", workspace["workspace_id"], "member@example.com")
        self._connect_github_user("member-1")

        with self.assertRaises(Exception):
            repo_service.index_repository(
                "https://github.com/acme/private",
                workspace_id=workspace["workspace_id"],
                user_id="member-1",
                user_email="member@example.com",
            )

        workspace_service.update_workspace_member_connector_manager(
            "admin-1",
            workspace["workspace_id"],
            "member@example.com",
            True,
        )
        with patch("src.backend.application.services.github.permissions.github_json_request", return_value={"id": 1}):
            with patch.object(repo_service, "index_repo", return_value={"repo_id": "repo"}) as index_repo:
                result = repo_service.index_repository(
                    "https://github.com/acme/private",
                    workspace_id=workspace["workspace_id"],
                    user_id="member-1",
                    user_email="member@example.com",
                )

        self.assertEqual(result, {"repo_id": "repo"})
        self.assertEqual(index_repo.call_args.kwargs["github_token"], "gh-token")

    def _connect_github_user(self, user_id: str) -> None:
        with database.session_scope() as session:
            session.add(
                GithubUserConnection(
                    user_id=user_id,
                    github_user_id="123",
                    login="octo",
                    access_token_encrypted=encrypt_token("gh-token"),
                    scopes="repo,read:user",
                )
            )


if __name__ == "__main__":
    unittest.main()
