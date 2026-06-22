import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.backend.application.services import workspace_service
from src.backend.application.services.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from src.backend.infrastructure import database


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database()
        self.patches = [
            patch.object(workspace_service, "DATA_DIR", self.data_dir),
            patch("src.backend.infrastructure.storage.paths.DATA_DIR", self.data_dir),
            patch.object(workspace_service, "CLI_STATE_FILE", self.data_dir / "cli-state.json"),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_create_workspace_adds_owner_membership(self):
        workspace = workspace_service.create_workspace(
            "admin-1",
            "Demo",
            owner_email="admin@example.com",
            owner_name="Admin User",
        )

        self.assertEqual(workspace["name"], "Demo")
        self.assertTrue(workspace["workspace_id"])
        self.assertEqual(workspace["owner_user_id"], "admin-1")
        self.assertTrue(workspace["can_manage"])
        self.assertEqual(
            workspace_service.list_workspaces(
                "admin-1",
                user_email="admin@example.com",
            ),
            [workspace],
        )

    def test_duplicate_names_fail_case_insensitively_for_same_owner(self):
        workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")

        with self.assertRaises(ValidationError):
            workspace_service.create_workspace("admin-1", " demo ", owner_email="admin@example.com")

    def test_same_name_is_allowed_for_different_owners(self):
        first = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin1@example.com")
        second = workspace_service.create_workspace("admin-2", "demo", owner_email="admin2@example.com")

        self.assertNotEqual(first["workspace_id"], second["workspace_id"])
        self.assertEqual(
            len(workspace_service.list_workspaces("admin-1", user_email="admin1@example.com")),
            1,
        )
        self.assertEqual(
            len(workspace_service.list_workspaces("admin-2", user_email="admin2@example.com")),
            1,
        )

    def test_member_only_sees_workspace_after_graph_node_exists(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        workspace_service.add_workspace_member(
            "admin-1",
            workspace["workspace_id"],
            "member@example.com",
        )

        member_workspaces = workspace_service.list_workspaces(
            "member-1",
            user_email="member@example.com",
        )
        self.assertEqual(member_workspaces, [])

        from src.backend.application.services.auth_service import AuthUser, GoogleIdentity, upsert_authenticated_user
        from src.backend.application.services.hierarchy_graph_service import create_hierarchy_node

        upsert_authenticated_user(
            GoogleIdentity("member-1", "member@example.com", "Member")
        )
        create_hierarchy_node(
            workspace["workspace_id"],
            AuthUser("admin-1", "admin@example.com", "Admin"),
            display_name="Member",
            assigned_user_id="member-1",
        )

        member_workspaces = workspace_service.list_workspaces(
            "member-1",
            user_email="member@example.com",
        )
        self.assertEqual(len(member_workspaces), 1)
        self.assertFalse(member_workspaces[0]["can_manage"])

    def test_unassigned_user_cannot_access_workspace(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")

        with self.assertRaises(ResourceNotFoundError):
            workspace_service.get_workspace(
                "member-1",
                workspace["workspace_id"],
                user_email="member@example.com",
            )

    def test_only_owner_can_delete_workspace(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")

        with self.assertRaises(PermissionDeniedError):
            workspace_service.delete_workspace("admin-2", workspace["workspace_id"])

    def test_delete_workspace_removes_metadata_and_storage(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        root = workspace_service.workspace_root(workspace["workspace_id"])
        (root / "indexes" / "repo.json").write_text("{}", encoding="utf-8")

        with patch.object(workspace_service, "list_indexes", return_value=[]):
            deleted = workspace_service.delete_workspace("admin-1", workspace["workspace_id"])

        self.assertEqual(deleted["workspace_id"], workspace["workspace_id"])
        self.assertEqual(
            workspace_service.list_workspaces("admin-1", user_email="admin@example.com"),
            [],
        )
        self.assertFalse(root.exists())

    def test_owner_cannot_be_removed_from_members(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")

        with self.assertRaises(ValidationError):
            workspace_service.remove_workspace_member(
                "admin-1",
                workspace["workspace_id"],
                "admin@example.com",
            )

    def test_owner_can_grant_connector_manager(self):
        workspace = workspace_service.create_workspace("admin-1", "Demo", owner_email="admin@example.com")
        workspace_service.add_workspace_member("admin-1", workspace["workspace_id"], "member@example.com")

        updated = workspace_service.update_workspace_member_connector_manager(
            "admin-1",
            workspace["workspace_id"],
            "member@example.com",
            True,
        )

        self.assertTrue(updated["connector_manager"])
        self.assertTrue(
            workspace_service.user_can_manage_workspace_connectors(
                "member-1",
                "member@example.com",
                workspace["workspace_id"],
            )
        )

    def test_get_active_workspace_clears_missing_cli_state(self):
        workspace_service.set_active_workspace_id("missing")

        with self.assertRaises(ResourceNotFoundError):
            workspace_service.get_active_workspace()

        self.assertIsNone(workspace_service.read_active_workspace_id())


if __name__ == "__main__":
    unittest.main()
