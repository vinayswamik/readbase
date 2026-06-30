import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.api.auth import require_authenticated_user
from src.backend.api.routes import api_router
from src.backend.application.services import workspace_service
from src.backend.application.services.auth_service import AuthUser, GoogleIdentity, upsert_authenticated_user
from src.backend.application.services.connectors.oauth_core import ConnectorOAuthStart
from src.backend.application.services.hierarchy_graph_service import create_hierarchy_node
from src.backend.infrastructure import database


class WorkspaceApiTests(unittest.TestCase):
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

    def test_unauthenticated_workspace_request_returns_401(self):
        response = self.client.get("/api/workspaces")

        self.assertEqual(response.status_code, 401)

    def test_any_authenticated_user_can_create_workspace(self):
        self._login_as(AuthUser("member-1", "member@example.com", "Member"))

        response = self.client.post("/api/workspaces", json={"name": "Demo"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["owner_user_id"], "member-1")
        self.assertTrue(body["can_manage"])

    def test_owner_can_rename_workspace(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()

        response = self.client.patch(
            f"/api/workspaces/{workspace['workspace_id']}",
            json={"name": "Renamed Demo"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Renamed Demo")
        self.assertEqual(body["workspace_id"], workspace["workspace_id"])

    def test_rename_rejects_duplicate_owned_workspace_name(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        first = self.client.post("/api/workspaces", json={"name": "Alpha"}).json()
        second = self.client.post("/api/workspaces", json={"name": "Beta"}).json()

        response = self.client.patch(
            f"/api/workspaces/{second['workspace_id']}",
            json={"name": " alpha "},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        message = str(payload.get("error") or payload.get("detail") or "").lower()
        self.assertIn("already exists", message)
        unchanged = self.client.get("/api/workspaces").json()["workspaces"]
        self.assertEqual(
            next(item for item in unchanged if item["workspace_id"] == first["workspace_id"])["name"],
            "Alpha",
        )

    def test_member_cannot_rename_workspace(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()
        graph_url = f"/api/workspaces/{workspace['workspace_id']}/graph"
        self.client.post(
            f"{graph_url}/nodes",
            json={
                "display_name": "Member",
                "invitee_email": "member@example.com",
                "relation": "Peer",
                "reason": "Needs access",
            },
        )

        upsert_authenticated_user(
            GoogleIdentity("member-1", "member@example.com", "Member")
        )
        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        response = self.client.patch(
            f"/api/workspaces/{workspace['workspace_id']}",
            json={"name": "Hijacked"},
        )

        self.assertEqual(response.status_code, 403)

    def test_join_code_endpoints_are_removed(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()

        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        join_response = self.client.post("/api/workspaces/join", json={"code": "BADCODE2"})
        code_response = self.client.get(
            f"/api/workspaces/{workspace['workspace_id']}/join-code"
        )

        self.assertIn(join_response.status_code, (404, 405))
        self.assertEqual(code_response.status_code, 404)

    def test_list_invites_for_email_node_invite(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()
        graph_url = f"/api/workspaces/{workspace['workspace_id']}/graph"

        invite_response = self.client.post(
            f"{graph_url}/nodes",
            json={
                "display_name": "New hire",
                "invitee_email": "pending@example.com",
                "relation": "Direct report",
                "reason": "Joining the platform team",
                "invitor_designation": "Engineering manager",
            },
        )
        self.assertEqual(invite_response.status_code, 200)
        invite_body = invite_response.json()
        self.assertIsNone(invite_body["node"])
        self.assertEqual(invite_body["invite"]["status"], "pending")
        self.assertEqual(invite_body["invite"]["relation"], "Direct report")

        invites_response = self.client.get("/api/invites")
        self.assertEqual(invites_response.status_code, 200)
        sent = invites_response.json()["sent"]
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["invitee_email"], "pending@example.com")
        self.assertEqual(sent[0]["invitor_name"], "Owner")

    def test_accept_and_reject_invite_via_api(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()
        graph_url = f"/api/workspaces/{workspace['workspace_id']}/graph"

        invite_response = self.client.post(
            f"{graph_url}/nodes",
            json={
                "display_name": "Analyst",
                "invitee_email": "member@example.com",
                "relation": "Peer",
                "reason": "Needs access",
            },
        )
        invite_id = invite_response.json()["invite"]["invite_id"]

        upsert_authenticated_user(
            GoogleIdentity("member-1", "member@example.com", "Member")
        )
        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        reject_response = self.client.post(f"/api/invites/{invite_id}/reject")
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["status"], "rejected")

        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        invite_response = self.client.post(
            f"{graph_url}/nodes",
            json={
                "display_name": "Analyst",
                "invitee_email": "member@example.com",
                "relation": "Peer",
                "reason": "Second chance",
            },
        )
        invite_id = invite_response.json()["invite"]["invite_id"]
        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        accept_response = self.client.post(f"/api/invites/{invite_id}/accept")
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.json()["status"], "active")

        workspaces = self.client.get("/api/workspaces").json()["workspaces"]
        self.assertEqual(len(workspaces), 1)

    def test_invitor_can_revert_pending_invite(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()
        graph_url = f"/api/workspaces/{workspace['workspace_id']}/graph"

        invite_response = self.client.post(
            f"{graph_url}/nodes",
            json={
                "display_name": "Analyst",
                "invitee_email": "member@example.com",
                "relation": "Peer",
                "reason": "Needs access",
            },
        )
        invite_id = invite_response.json()["invite"]["invite_id"]

        revert_response = self.client.post(f"/api/invites/{invite_id}/revert")
        self.assertEqual(revert_response.status_code, 200)
        self.assertEqual(revert_response.json()["status"], "reverted")

        upsert_authenticated_user(
            GoogleIdentity("member-1", "member@example.com", "Member")
        )
        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        accept_response = self.client.post(f"/api/invites/{invite_id}/accept")
        self.assertEqual(accept_response.status_code, 400)

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
        upsert_authenticated_user(
            GoogleIdentity("member-1", "member@example.com", "Member")
        )
        create_hierarchy_node(
            workspace["workspace_id"],
            AuthUser("admin-1", "admin@example.com", "Admin"),
            display_name="Member",
            assigned_user_id="member-1",
        )

        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        member_response = self.client.get("/api/workspaces")
        self._login_as(AuthUser("other-1", "other@example.com", "Other"))
        other_response = self.client.get("/api/workspaces")

        self.assertEqual(member_response.status_code, 200)
        self.assertEqual(len(member_response.json()["workspaces"]), 1)
        self.assertEqual(other_response.status_code, 200)
        self.assertEqual(other_response.json()["workspaces"], [])

    def test_member_can_leave_workspace(self):
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
        upsert_authenticated_user(
            GoogleIdentity("member-1", "member@example.com", "Member")
        )
        create_hierarchy_node(
            workspace["workspace_id"],
            AuthUser("admin-1", "admin@example.com", "Admin"),
            display_name="Member",
            assigned_user_id="member-1",
        )

        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        leave_response = self.client.post(
            f"/api/workspaces/{workspace['workspace_id']}/leave",
            json={},
        )
        self.assertEqual(leave_response.status_code, 200)
        self.assertEqual(self.client.get("/api/workspaces").json()["workspaces"], [])

        self._login_as(AuthUser("admin-1", "admin@example.com", "Admin"))
        owner_leave = self.client.post(
            f"/api/workspaces/{workspace['workspace_id']}/leave",
            json={},
        )
        self.assertEqual(owner_leave.status_code, 400)

    def test_link_invite_can_be_created_previewed_and_accepted(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()
        graph_url = f"/api/workspaces/{workspace['workspace_id']}/graph"

        invite_response = self.client.post(
            f"{graph_url}/nodes",
            json={
                "display_name": "Link hire",
                "invite_method": "link",
                "relation": "Peer",
                "reason": "Join via shared link",
            },
        )
        self.assertEqual(invite_response.status_code, 200)
        invite = invite_response.json()["invite"]
        self.assertEqual(invite["invite_method"], "link")
        self.assertTrue(invite["join_token"])
        self.assertEqual(invite["join_path"], f"/?join={invite['join_token']}")

        upsert_authenticated_user(
            GoogleIdentity("member-1", "member@example.com", "Member")
        )
        self._login_as(AuthUser("member-1", "member@example.com", "Member"))
        preview = self.client.get(f"/api/invites/join/{invite['join_token']}")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["invite_id"], invite["invite_id"])

        accept_response = self.client.post(f"/api/invites/{invite['invite_id']}/accept")
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(len(self.client.get("/api/workspaces").json()["workspaces"]), 1)

    def test_link_invite_token_omitted_from_invite_list(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()
        graph_url = f"/api/workspaces/{workspace['workspace_id']}/graph"

        invite_response = self.client.post(
            f"{graph_url}/nodes",
            json={
                "display_name": "Link hire",
                "invite_method": "link",
                "relation": "Peer",
                "reason": "Join via shared link",
            },
        )
        created = invite_response.json()["invite"]
        self.assertTrue(created["join_token"])

        listed = self.client.get("/api/invites").json()["sent"]
        self.assertEqual(len(listed), 1)
        self.assertIsNone(listed[0]["join_token"])
        self.assertIsNone(listed[0]["join_path"])

    def test_pending_invitee_cannot_access_workspace_apis(self):
        self._login_as(AuthUser("owner-1", "owner@example.com", "Owner"))
        workspace = self.client.post("/api/workspaces", json={"name": "Demo"}).json()
        graph_url = f"/api/workspaces/{workspace['workspace_id']}/graph"

        self.client.post(
            f"{graph_url}/nodes",
            json={
                "display_name": "Pending hire",
                "invitee_email": "pending@example.com",
                "relation": "Peer",
                "reason": "Awaiting acceptance",
            },
        )

        upsert_authenticated_user(
            GoogleIdentity("pending-1", "pending@example.com", "Pending")
        )
        self._login_as(AuthUser("pending-1", "pending@example.com", "Pending"))
        response = self.client.get(f"/api/workspaces/{workspace['workspace_id']}/repos")
        self.assertEqual(response.status_code, 403)

    def test_missing_slack_config_returns_400(self):
        self._login_as(AuthUser("member-1", "member@example.com", "Member"))

        with patch.dict("os.environ", {"SLACK_CLIENT_ID": "", "SLACK_CLIENT_SECRET": ""}):
            response = self.client.get("/api/me/integrations/slack/start", follow_redirects=False)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "SLACK_CLIENT_ID is not configured.")

    def test_slack_oauth_returns_to_starting_workspace(self):
        workspace = workspace_service.create_workspace(
            "admin-1",
            "Demo",
            owner_email="admin@example.com",
            owner_name="Admin",
        )
        self._login_as(AuthUser("admin-1", "admin@example.com", "Admin"))

        with (
            patch(
                "src.backend.api.routes.slack.create_slack_oauth_start",
                return_value=ConnectorOAuthStart(state="state-1", code_verifier="verifier-1"),
            ),
            patch("src.backend.api.routes.slack.build_slack_authorize_url", return_value="https://slack.test/oauth"),
        ):
            start_response = self.client.get(
                f"/api/me/integrations/slack/start?workspace_id={workspace['workspace_id']}",
                follow_redirects=False,
            )

        self.assertEqual(start_response.status_code, 302)
        self.assertEqual(start_response.headers["location"], "https://slack.test/oauth")

        with patch("src.backend.api.routes.slack.exchange_slack_code_for_connection", return_value={}) as exchange:
            callback_response = self.client.get(
                "/api/me/integrations/slack/callback?code=code-1&state=state-1",
                cookies={
                    "readbase_slack_oauth_state": "state-1",
                    "readbase_slack_pkce": "verifier-1",
                    "readbase_slack_return_workspace": workspace["workspace_id"],
                },
                follow_redirects=False,
            )

        self.assertEqual(callback_response.status_code, 303)
        parsed = urlparse(callback_response.headers["location"])
        params = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/")
        self.assertEqual(params["slack_connected"], ["1"])
        self.assertEqual(params["connector"], ["slack"])
        self.assertEqual(params["workspace_id"], [workspace["workspace_id"]])

    def test_slack_oauth_returns_already_connected_when_workspace_linked(self):
        workspace = workspace_service.create_workspace(
            "admin-1",
            "Demo",
            owner_email="admin@example.com",
            owner_name="Admin",
        )
        self._login_as(AuthUser("admin-1", "admin@example.com", "Admin"))

        with patch(
            "src.backend.api.routes.slack.exchange_slack_code_for_connection",
            return_value={"already_connected": True},
        ):
            callback_response = self.client.get(
                "/api/me/integrations/slack/callback?code=code-1&state=state-1",
                cookies={
                    "readbase_slack_oauth_state": "state-1",
                    "readbase_slack_pkce": "verifier-1",
                    "readbase_slack_return_workspace": workspace["workspace_id"],
                },
                follow_redirects=False,
            )

        self.assertEqual(callback_response.status_code, 303)
        parsed = urlparse(callback_response.headers["location"])
        params = parse_qs(parsed.query)
        self.assertEqual(params["slack_connected"], ["already"])

    def _login_as(self, user: AuthUser) -> None:
        self.app.dependency_overrides[require_authenticated_user] = lambda: user


if __name__ == "__main__":
    unittest.main()
