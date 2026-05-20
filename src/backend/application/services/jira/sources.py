from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.backend.application.services.workspace_service import (
    user_can_access_workspace,
    user_can_manage_workspace_connectors,
)
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import JiraUserSite, Workspace, WorkspaceJiraSource, utc_now

from .auth import get_valid_jira_access_token
from .http import jira_request
from .serializers import public_source
from .utils import optional_str, required_payload


def list_visible_jira_projects(user_id: str, query: str = "") -> list[dict]:
    access_token = get_valid_jira_access_token(user_id)
    with session_scope() as session:
        site_rows = session.scalars(select(JiraUserSite).where(JiraUserSite.user_id == user_id)).all()
        sites = [
            {
                "cloud_id": site.cloud_id,
                "site_name": site.site_name,
                "site_url": site.site_url,
            }
            for site in site_rows
        ]
        if not sites:
            raise ValidationError("Connect Jira before selecting a project.")

    projects: list[dict] = []
    for site in sites:
        params = {"maxResults": "50"}
        if query.strip():
            params["query"] = query.strip()
        data = jira_request(site["cloud_id"], "/rest/api/3/project/search", access_token, query=params)
        for project in data.get("values", []) if isinstance(data, dict) else []:
            project_id = optional_str(project.get("id"))
            project_key = optional_str(project.get("key"))
            project_name = optional_str(project.get("name"))
            if not project_id or not project_key or not project_name:
                continue
            projects.append(
                {
                    "cloud_id": site["cloud_id"],
                    "site_name": site["site_name"],
                    "site_url": site["site_url"],
                    "project_id": project_id,
                    "project_key": project_key,
                    "project_name": project_name,
                }
            )
    return projects


def list_workspace_jira_sources(workspace_id: str, user_id: str) -> list[dict]:
    with session_scope() as session:
        sources = session.scalars(
            select(WorkspaceJiraSource)
            .where(WorkspaceJiraSource.workspace_id == workspace_id.strip())
            .order_by(WorkspaceJiraSource.created_at.desc())
        ).all()
        connected_cloud_ids = {
            site.cloud_id
            for site in session.scalars(select(JiraUserSite).where(JiraUserSite.user_id == user_id)).all()
        }
        return [
            public_source(source, user_access=("connected" if source.cloud_id in connected_cloud_ids else "connect_jira"))
            for source in sources
        ]


def add_workspace_jira_source(
    workspace_id: str,
    actor_user_id: str,
    actor_email: str,
    payload: dict,
) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    cloud_id = required_payload(payload, "cloud_id")
    project_id = required_payload(payload, "project_id")
    project_key = required_payload(payload, "project_key")
    project_name = required_payload(payload, "project_name")
    site_name = required_payload(payload, "site_name")
    site_url = required_payload(payload, "site_url")

    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id.strip())
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        site = session.scalar(
            select(JiraUserSite).where(
                JiraUserSite.user_id == actor_user_id,
                JiraUserSite.cloud_id == cloud_id,
            )
        )
        if site is None:
            raise PermissionDeniedError("Connect Jira with access to this site before adding the project.")
        source = WorkspaceJiraSource(
            source_id=f"jira-{uuid4().hex[:16]}",
            workspace_id=workspace.workspace_id,
            cloud_id=cloud_id,
            site_name=site_name,
            site_url=site_url,
            project_id=project_id,
            project_key=project_key,
            project_name=project_name,
            added_by_user_id=actor_user_id,
            sync_owner_user_id=actor_user_id,
            next_sync_at=utc_now(),
        )
        session.add(source)
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("Jira project is already connected to this workspace.") from exc
        return public_source(source, user_access="connected")


def remove_workspace_jira_source(workspace_id: str, source_id: str, actor_user_id: str, actor_email: str) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    with session_scope() as session:
        source = session.get(WorkspaceJiraSource, source_id.strip())
        if source is None or source.workspace_id != workspace_id.strip():
            raise ResourceNotFoundError("Jira source not found.")
        public = public_source(source, user_access="unknown")
        session.delete(source)
        return public


def require_connector_manager(user_id: str, user_email: str, workspace_id: str) -> None:
    if not user_can_access_workspace(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Workspace access required.")
    if not user_can_manage_workspace_connectors(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Connector manager access required.")
