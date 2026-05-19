import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.api.auth import require_authenticated_user
from src.backend.api.routes import api_router
from src.backend.application.services import workspace_service
from src.backend.application.services.auth_service import AuthUser
from src.backend.infrastructure import database


class WorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database(seed_admins=False)
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_unauthenticated_workspace_request_returns_401(self):
        response = self.client.get("/api/workspaces")

        self.assertEqual(response.status_code, 401)

    def test_member_cannot_create_workspace(self):
        self._login_as(AuthUser("member-1", "member@example.com", "Member", "member"))

        response = self.client.post("/api/workspaces", json={"name": "Demo"})

        self.assertEqual(response.status_code, 403)

    def test_workspace_list_differs_by_membership(self):
        workspace = workspace_service.create_workspace(
            "admin-1",
            "Demo",
            owner_email="admin@example.com",
            owner_name="Admin",
        )
        workspace_service.add_workspace_member(
            "admin-1",
            workspace["workspace_id"],
            "member@example.com",
        )

        self._login_as(AuthUser("member-1", "member@example.com", "Member", "member"))
        member_response = self.client.get("/api/workspaces")
        self._login_as(AuthUser("other-1", "other@example.com", "Other", "member"))
        other_response = self.client.get("/api/workspaces")

        self.assertEqual(member_response.status_code, 200)
        self.assertEqual(len(member_response.json()["workspaces"]), 1)
        self.assertEqual(other_response.status_code, 200)
        self.assertEqual(other_response.json()["workspaces"], [])

    def _login_as(self, user: AuthUser) -> None:
        self.app.dependency_overrides[require_authenticated_user] = lambda: user


if __name__ == "__main__":
    unittest.main()
