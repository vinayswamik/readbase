import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.api.auth import require_authenticated_user
from src.backend.api.routes import api_router
from src.backend.application.services import workspace_service
from src.backend.application.services.auth_service import AuthUser, GoogleIdentity, upsert_authenticated_user
from src.backend.application.services.hierarchy_graph_service import create_hierarchy_node
from src.backend.infrastructure import database


class NotificationApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database()
        self.app = FastAPI()
        self.app.include_router(api_router)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_leave_workspace_creates_notification_for_owner(self):
        workspace = workspace_service.create_workspace(
            "owner-1",
            "Demo",
            owner_email="owner@example.com",
            owner_name="Owner",
        )
        workspace_service.add_workspace_member(
            "owner-1",
            workspace["workspace_id"],
            "member@example.com",
        )
        upsert_authenticated_user(
            GoogleIdentity("member-1", "member@example.com", "Member")
        )
        create_hierarchy_node(
            workspace["workspace_id"],
            AuthUser("owner-1", "owner@example.com", "Owner"),
            display_name="Member",
            assigned_user_id="member-1",
        )

        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        leave_response = self.client.post(
            f"/api/workspaces/{workspace['workspace_id']}/leave",
            json={},
        )
        self.assertEqual(leave_response.status_code, 200)

        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        notifications_response = self.client.get("/api/notifications")
        self.assertEqual(notifications_response.status_code, 200)
        notifications = notifications_response.json()["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["type"], "workspace_member_left")
        self.assertEqual(notifications[0]["workspace_id"], workspace["workspace_id"])
        self.assertEqual(notifications[0]["actor_user_id"], "member-1")
        self.assertIn("Member left Demo", notifications[0]["body"])

    def test_unauthenticated_notifications_request_returns_401(self):
        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, 401)

    def _login_as(self, user: AuthUser) -> None:
        self.app.dependency_overrides[require_authenticated_user] = lambda: user
