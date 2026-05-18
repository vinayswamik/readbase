import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.backend.application.services.exceptions import ResourceNotFoundError, ValidationError
from src.backend.application.services import workspace_service


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.patches = [
            patch.object(workspace_service, "DATA_DIR", self.data_dir),
            patch.object(workspace_service, "WORKSPACES_DIR", self.data_dir / "workspaces"),
            patch.object(workspace_service, "WORKSPACES_MANIFEST", self.data_dir / "workspaces.json"),
            patch.object(workspace_service, "CLI_STATE_FILE", self.data_dir / "cli-state.json"),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def test_create_workspace_succeeds(self):
        workspace = workspace_service.create_workspace("user-1", "Demo")

        self.assertEqual(workspace["name"], "Demo")
        self.assertTrue(workspace["workspace_id"])
        self.assertEqual(workspace_service.list_workspaces("user-1"), [workspace])

    def test_duplicate_names_fail_case_insensitively_for_same_owner(self):
        workspace_service.create_workspace("user-1", "Demo")

        with self.assertRaises(ValidationError):
            workspace_service.create_workspace("user-1", " demo ")

    def test_same_name_is_allowed_for_different_owners(self):
        first = workspace_service.create_workspace("user-1", "Demo")
        second = workspace_service.create_workspace("user-2", "demo")

        self.assertNotEqual(first["workspace_id"], second["workspace_id"])
        self.assertEqual(len(workspace_service.list_workspaces("user-1")), 1)
        self.assertEqual(len(workspace_service.list_workspaces("user-2")), 1)

    def test_delete_workspace_removes_metadata_and_storage(self):
        workspace = workspace_service.create_workspace("user-1", "Demo")
        root = workspace_service.workspace_root(workspace["workspace_id"])
        (root / "indexes").mkdir(parents=True)
        (root / "indexes" / "repo.json").write_text("{}", encoding="utf-8")

        with patch.object(workspace_service, "list_indexes", return_value=[]):
            deleted = workspace_service.delete_workspace("user-1", workspace["workspace_id"])

        self.assertEqual(deleted["workspace_id"], workspace["workspace_id"])
        self.assertEqual(workspace_service.list_workspaces("user-1"), [])
        self.assertFalse(root.exists())

    def test_delete_workspace_for_another_owner_returns_not_found(self):
        workspace = workspace_service.create_workspace("user-1", "Demo")

        with self.assertRaises(ResourceNotFoundError):
            workspace_service.delete_workspace("user-2", workspace["workspace_id"])

    def test_get_active_workspace_clears_missing_cli_state(self):
        workspace_service.set_active_workspace_id("missing")

        with self.assertRaises(ResourceNotFoundError):
            workspace_service.get_active_workspace()

        self.assertIsNone(workspace_service.read_active_workspace_id())


if __name__ == "__main__":
    unittest.main()
