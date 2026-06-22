import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.backend.application.services import workspace_service
from src.backend.application.services.exceptions import ResourceNotFoundError
from src.backend.infrastructure import database
from src.backend.infrastructure.storage.deployment import DeploymentMode
from src.backend.infrastructure.storage.paths import build_cli_context, build_workspace_context
from src.backend.infrastructure.storage.resolver import resolve_storage_context


class StorageContextTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.env_patch = patch.dict(
            os.environ,
            {
                "READBASE_DATA_DIR": str(self.data_dir),
                "READBASE_DEPLOYMENT_MODE": "saas",
            },
            clear=False,
        )
        self.env_patch.start()
        self.data_dir_patch = patch("src.backend.infrastructure.storage.paths.DATA_DIR", self.data_dir)
        self.data_dir_patch.start()

        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database()

    def tearDown(self):
        self.data_dir_patch.stop()
        self.env_patch.stop()
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_saas_paths_use_owner_and_workspace(self):
        context = build_workspace_context(
            deployment=DeploymentMode.SAAS,
            owner_user_id="owner-1",
            workspace_id="ws-1",
        )
        self.assertEqual(
            context.workspace_root,
            self.data_dir / "owners" / "owner-1" / "workspaces" / "ws-1",
        )
        self.assertEqual(context.repos_dir, context.workspace_root / "repos")
        self.assertEqual(context.indexes_dir, context.workspace_root / "indexes")
        self.assertEqual(context.chroma_dir, context.workspace_root / "chroma")
        self.assertEqual(context.legacy_workspace_root, self.data_dir / "workspaces" / "ws-1")

    def test_customer_paths_use_org_project_root(self):
        org_root = self.data_dir / "customer-root"
        with patch.dict(os.environ, {"READBASE_ORG_STORAGE_ROOT": str(org_root)}, clear=False):
            with patch("src.backend.infrastructure.storage.deployment.org_storage_root", return_value=org_root):
                context = build_workspace_context(
                    deployment=DeploymentMode.CUSTOMER,
                    owner_user_id="owner-1",
                    workspace_id="ws-1",
                )
        self.assertEqual(context.workspace_root, org_root / "projects" / "ws-1")
        self.assertIsNone(context.legacy_workspace_root)

    def test_cli_context_uses_global_data_dirs(self):
        context = build_cli_context()
        self.assertEqual(context.repos_dir, self.data_dir / "repos")
        self.assertEqual(context.indexes_dir, self.data_dir / "indexes")
        self.assertEqual(context.chroma_dir, self.data_dir / "chroma")

    def test_resolver_uses_workspace_owner(self):
        workspace = workspace_service.create_workspace(
            "owner-abc",
            "Demo",
            owner_email="owner@example.com",
        )
        context = resolve_storage_context(workspace["workspace_id"])
        self.assertEqual(context.owner_user_id, "owner-abc")
        self.assertEqual(context.workspace_id, workspace["workspace_id"])
        self.assertIn("owner-abc", str(context.workspace_root))

    def test_resolver_raises_for_missing_workspace(self):
        with self.assertRaises(ResourceNotFoundError):
            resolve_storage_context("missing-workspace")


if __name__ == "__main__":
    unittest.main()
