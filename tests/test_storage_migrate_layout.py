import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.backend.application.services import workspace_service
from src.backend.infrastructure import database
from src.backend.infrastructure.storage.migrate_layout import migrate_legacy_layout
from src.backend.infrastructure.storage.paths import legacy_workspace_root, saas_workspace_root


class StorageMigrateLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database()
        self.data_dir_patch = patch("src.backend.infrastructure.storage.paths.DATA_DIR", self.data_dir)
        self.data_dir_patch.start()
        self.migrate_data_dir_patch = patch(
            "src.backend.infrastructure.storage.migrate_layout.DATA_DIR",
            self.data_dir,
        )
        self.migrate_data_dir_patch.start()

    def tearDown(self):
        self.migrate_data_dir_patch.stop()
        self.data_dir_patch.stop()
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_migrate_moves_legacy_workspace_to_owner_layout(self):
        with patch.object(workspace_service, "resolve_storage_context", return_value=MagicMock()):
            workspace = workspace_service.create_workspace(
                "owner-1",
                "Demo",
                owner_email="owner@example.com",
            )
        legacy = legacy_workspace_root(workspace["workspace_id"])
        legacy.mkdir(parents=True)
        (legacy / "indexes").mkdir()
        (legacy / "indexes" / "repo.json").write_text("{}", encoding="utf-8")

        results = migrate_legacy_layout(dry_run=False)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].moved)
        destination = saas_workspace_root("owner-1", workspace["workspace_id"])
        self.assertTrue((destination / "indexes" / "repo.json").exists())
        self.assertFalse(legacy.exists())


if __name__ == "__main__":
    unittest.main()
