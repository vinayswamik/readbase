import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.backend.application.services import organization_service, workspace_service
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.infrastructure import database
from src.backend.infrastructure.storage.resolver import resolve_storage_context


class OrganizationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database()
        self.data_dir_patch = patch("src.backend.infrastructure.storage.paths.DATA_DIR", self.data_dir)
        self.data_dir_patch.start()

    def tearDown(self):
        self.data_dir_patch.stop()
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_create_organization_and_assign_workspace(self):
        org = organization_service.create_organization(
            "admin-1",
            "Acme",
            str(self.data_dir / "acme-storage"),
            owner_email="admin@example.com",
        )
        workspace = workspace_service.create_workspace(
            "admin-1",
            "Project One",
            owner_email="admin@example.com",
        )
        linked = organization_service.assign_workspace_to_organization(
            "admin-1",
            workspace["workspace_id"],
            org["org_id"],
        )
        self.assertEqual(linked["organization_id"], org["org_id"])

        context = resolve_storage_context(workspace["workspace_id"])
        self.assertIn("acme-storage", str(context.workspace_root))

    def test_non_admin_cannot_update_org_storage(self):
        org = organization_service.create_organization(
            "admin-1",
            "Acme",
            str(self.data_dir / "acme-storage"),
            owner_email="admin@example.com",
        )
        with self.assertRaises(PermissionDeniedError):
            organization_service.update_organization_storage(
                "member-1",
                org["org_id"],
                storage_root=str(self.data_dir / "other"),
            )

    def test_duplicate_org_name_fails(self):
        organization_service.create_organization(
            "admin-1",
            "Acme",
            str(self.data_dir / "acme-storage"),
            owner_email="admin@example.com",
        )
        with self.assertRaises(ValidationError):
            organization_service.create_organization(
                "admin-1",
                " acme ",
                str(self.data_dir / "acme-storage-2"),
                owner_email="admin@example.com",
            )


if __name__ == "__main__":
    unittest.main()
