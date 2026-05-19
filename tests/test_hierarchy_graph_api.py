import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.api.auth import require_authenticated_user
from src.backend.api.routes import api_router
from src.backend.application.services import workspace_service
from src.backend.application.services.auth_service import (
    AuthUser,
    GoogleIdentity,
    upsert_authenticated_user,
)
from src.backend.infrastructure import database


class HierarchyGraphApiTests(unittest.TestCase):
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
        self.admin = AuthUser("admin-1", "admin@example.com", "Admin", "admin")
        self.member = AuthUser("member-1", "member@example.com", "Member", "member")
        self.other_member = AuthUser("member-2", "other@example.com", "Other", "member")
        self.third_member = AuthUser("member-3", "third@example.com", "Third", "member")
        self.outsider = AuthUser("outsider", "outsider@example.com", "Outsider", "member")
        self.workspace = workspace_service.create_workspace(
            self.admin.user_id,
            "Demo",
            owner_email=self.admin.email,
            owner_name=self.admin.name,
        )
        for member in (self.member, self.other_member, self.third_member):
            workspace_service.add_workspace_member(
                self.admin.user_id,
                self.workspace["workspace_id"],
                member.email,
            )
            upsert_authenticated_user(
                GoogleIdentity(member.user_id, member.email, member.name),
                role=member.role,
            )

    def tearDown(self):
        self.app.dependency_overrides.clear()
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_cannot_create_node_without_logged_in_workspace_assignee(self):
        self._login_as(self.admin)

        pending = workspace_service.add_workspace_member(
            self.admin.user_id,
            self.workspace["workspace_id"],
            "pending@example.com",
        )
        no_assignee = self.client.post(
            self._graph_url("/nodes"),
            json={"display_name": "No assignee"},
        )
        pending_assignee = self.client.post(
            self._graph_url("/nodes"),
            json={
                "display_name": "Pending",
                "assigned_user_id": pending["user_id"] or "pending-user",
            },
        )
        outsider_assignee = self.client.post(
            self._graph_url("/nodes"),
            json={
                "display_name": "Outsider",
                "assigned_user_id": self.outsider.user_id,
            },
        )

        self.assertEqual(no_assignee.status_code, 422)
        self.assertEqual(pending_assignee.status_code, 400)
        self.assertEqual(outsider_assignee.status_code, 400)

    def test_cannot_assign_user_to_multiple_nodes(self):
        self._login_as(self.admin)
        self._create_node("Admin", self.admin.user_id)

        duplicate = self.client.post(
            self._graph_url("/nodes"),
            json={
                "display_name": "Duplicate admin",
                "assigned_user_id": self.admin.user_id,
            },
        )

        self.assertEqual(duplicate.status_code, 400)

    def test_admin_can_create_delete_rename_and_reparent_any_node(self):
        self._login_as(self.admin)
        root = self._create_node("Admin", self.admin.user_id)
        child = self._create_node("Member", self.member.user_id, root["node"]["node_id"])
        sibling = self._create_node("Other", self.other_member.user_id, root["node"]["node_id"])

        rename = self.client.patch(
            self._graph_url(f"/nodes/{child['node']['node_id']}"),
            json={"display_name": "Renamed member"},
        )
        reassign = self.client.patch(
            self._graph_url(f"/nodes/{child['node']['node_id']}"),
            json={"assigned_user_id": self.third_member.user_id},
        )
        reparent = self.client.patch(
            self._graph_url(f"/nodes/{child['node']['node_id']}"),
            json={"parent_node_id": sibling["node"]["node_id"]},
        )

        self.assertEqual(rename.status_code, 200)
        self.assertEqual(rename.json()["display_name"], "Renamed member")
        self.assertEqual(reassign.status_code, 200)
        self.assertEqual(reassign.json()["assigned_user_id"], self.third_member.user_id)
        self.assertEqual(reparent.status_code, 200)
        graph = self.client.get(self._graph_url("")).json()
        self.assertTrue(
            any(
                edge["parent_node_id"] == sibling["node"]["node_id"]
                and edge["child_node_id"] == child["node"]["node_id"]
                for edge in graph["connections"]
            )
        )
        delete = self.client.delete(self._graph_url(f"/nodes/{child['node']['node_id']}"))
        self.assertEqual(delete.status_code, 200)

    def test_member_can_create_immediate_child_only_under_own_node(self):
        self._login_as(self.admin)
        root = self._create_node("Admin", self.admin.user_id)
        member_node = self._create_node("Member", self.member.user_id, root["node"]["node_id"])
        self._login_as(self.member)

        missing_parent = self.client.post(
            self._graph_url("/nodes"),
            json={
                "display_name": "Other",
                "assigned_user_id": self.other_member.user_id,
            },
        )
        under_root = self.client.post(
            self._graph_url("/nodes"),
            json={
                "display_name": "Other",
                "assigned_user_id": self.other_member.user_id,
                "parent_node_id": root["node"]["node_id"],
            },
        )
        created = self.client.post(
            self._graph_url("/nodes"),
            json={
                "display_name": "Other",
                "assigned_user_id": self.other_member.user_id,
                "parent_node_id": member_node["node"]["node_id"],
            },
        )

        self.assertEqual(missing_parent.status_code, 403)
        self.assertEqual(under_root.status_code, 403)
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["node"]["assigned_user_id"], self.other_member.user_id)

    def test_member_without_own_node_cannot_create_child(self):
        self._login_as(self.admin)
        root = self._create_node("Admin", self.admin.user_id)
        self._login_as(self.member)

        response = self.client.post(
            self._graph_url("/nodes"),
            json={
                "display_name": "Other",
                "assigned_user_id": self.other_member.user_id,
                "parent_node_id": root["node"]["node_id"],
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_member_delete_rules_are_limited_to_immediate_children(self):
        self._login_as(self.admin)
        root = self._create_node("Admin", self.admin.user_id)
        member_node = self._create_node("Member", self.member.user_id, root["node"]["node_id"])
        child = self._create_node("Other", self.other_member.user_id, member_node["node"]["node_id"])
        grandchild = self._create_node("Third", self.third_member.user_id, child["node"]["node_id"])
        self._login_as(self.member)

        delete_self = self.client.delete(self._graph_url(f"/nodes/{member_node['node']['node_id']}"))
        delete_parent = self.client.delete(self._graph_url(f"/nodes/{root['node']['node_id']}"))
        delete_descendant = self.client.delete(
            self._graph_url(f"/nodes/{grandchild['node']['node_id']}")
        )
        delete_child_with_children = self.client.delete(
            self._graph_url(f"/nodes/{child['node']['node_id']}")
        )

        self.assertEqual(delete_self.status_code, 403)
        self.assertEqual(delete_parent.status_code, 403)
        self.assertEqual(delete_descendant.status_code, 403)
        self.assertEqual(delete_child_with_children.status_code, 403)

        self._login_as(self.admin)
        self.client.delete(self._graph_url(f"/nodes/{grandchild['node']['node_id']}"))
        self._login_as(self.member)
        delete_child = self.client.delete(self._graph_url(f"/nodes/{child['node']['node_id']}"))

        self.assertEqual(delete_child.status_code, 200)

    def test_any_workspace_user_can_update_node_position(self):
        self._login_as(self.admin)
        root = self._create_node("Admin", self.admin.user_id)
        self._login_as(self.member)

        response = self.client.patch(
            self._graph_url(f"/nodes/{root['node']['node_id']}"),
            json={"x": 240, "y": 320},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["x"], 240)
        self.assertEqual(response.json()["y"], 320)

    def test_member_cannot_rename_reassign_or_reparent_nodes(self):
        self._login_as(self.admin)
        root = self._create_node("Admin", self.admin.user_id)
        member_node = self._create_node("Member", self.member.user_id, root["node"]["node_id"])
        child = self._create_node("Other", self.other_member.user_id, member_node["node"]["node_id"])
        self._login_as(self.member)

        rename = self.client.patch(
            self._graph_url(f"/nodes/{child['node']['node_id']}"),
            json={"display_name": "Member renamed"},
        )
        reassign = self.client.patch(
            self._graph_url(f"/nodes/{child['node']['node_id']}"),
            json={"assigned_user_id": self.third_member.user_id},
        )
        reparent = self.client.patch(
            self._graph_url(f"/nodes/{child['node']['node_id']}"),
            json={"parent_node_id": root["node"]["node_id"]},
        )

        self.assertEqual(rename.status_code, 403)
        self.assertEqual(reassign.status_code, 403)
        self.assertEqual(reparent.status_code, 403)

    def test_single_parent_and_cycle_protections_still_apply(self):
        self._login_as(self.admin)
        root = self._create_node("Admin", self.admin.user_id)
        child = self._create_node("Member", self.member.user_id, root["node"]["node_id"])
        grandchild = self._create_node("Other", self.other_member.user_id, child["node"]["node_id"])

        self_edge = self.client.post(
            self._graph_url("/connections"),
            json={
                "parent_node_id": child["node"]["node_id"],
                "child_node_id": child["node"]["node_id"],
            },
        )
        duplicate_or_second_parent = self.client.post(
            self._graph_url("/connections"),
            json={
                "parent_node_id": root["node"]["node_id"],
                "child_node_id": grandchild["node"]["node_id"],
            },
        )
        self.client.delete(self._graph_url(f"/connections/{child['connection']['connection_id']}"))
        cycle = self.client.post(
            self._graph_url("/connections"),
            json={
                "parent_node_id": grandchild["node"]["node_id"],
                "child_node_id": child["node"]["node_id"],
            },
        )

        self.assertEqual(self_edge.status_code, 400)
        self.assertEqual(duplicate_or_second_parent.status_code, 400)
        self.assertEqual(cycle.status_code, 400)

    def test_workspace_access_is_required(self):
        self._login_as(self.outsider)

        response = self.client.get(self._graph_url(""))

        self.assertEqual(response.status_code, 403)

    def _login_as(self, user: AuthUser) -> None:
        self.app.dependency_overrides[require_authenticated_user] = lambda: user

    def _create_node(
        self,
        display_name: str,
        assigned_user_id: str,
        parent_node_id: str | None = None,
    ) -> dict:
        response = self.client.post(
            self._graph_url("/nodes"),
            json={
                "display_name": display_name,
                "assigned_user_id": assigned_user_id,
                "parent_node_id": parent_node_id,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _graph_url(self, path: str) -> str:
        return f"/api/workspaces/{self.workspace['workspace_id']}/graph{path}"


if __name__ == "__main__":
    unittest.main()
