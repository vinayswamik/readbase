from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.backend.application.services.workspace_service import (
    user_can_access_workspace,
    user_can_manage_workspace_connectors,
)
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    OrgSource,
    JiraIndexedItem,
    JiraUserSite,
    Workspace,
    WorkspaceJiraSite,
    WorkspaceJiraSource,
    WorkspaceMember,
    WorkspaceSourceSubscription,
    utc_now,
)

from .auth import get_valid_jira_access_token
from .http import jira_request
from .serializers import public_source, public_workspace_jira_site
from .sync import rebuild_workspace_jira_index
from .utils import optional_str, required_payload


def get_workspace_jira_site(workspace_id: str) -> dict:
    normalized_workspace_id = workspace_id.strip()
    with session_scope() as session:
        site = session.get(WorkspaceJiraSite, normalized_workspace_id)
        if site is not None:
            return {"connected": True, "site": public_workspace_jira_site(site)}

        legacy_source = session.scalar(
            select(WorkspaceJiraSource)
            .where(WorkspaceJiraSource.workspace_id == normalized_workspace_id)
            .order_by(WorkspaceJiraSource.created_at.asc())
        )
        if legacy_source is None:
            return {"connected": False, "site": None}

        site = WorkspaceJiraSite(
            workspace_id=normalized_workspace_id,
            cloud_id=legacy_source.cloud_id,
            site_name=legacy_source.site_name,
            site_url=legacy_source.site_url,
            connected_by_user_id=legacy_source.added_by_user_id,
        )
        session.add(site)
        session.flush()
        return {"connected": True, "site": public_workspace_jira_site(site)}


def connect_workspace_jira_site(
    workspace_id: str,
    actor_user_id: str,
    actor_email: str,
    cloud_id: str,
) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    normalized_workspace_id = workspace_id.strip()
    normalized_cloud_id = cloud_id.strip()
    if not normalized_cloud_id:
        raise ValidationError("cloud_id is required.")

    with session_scope() as session:
        workspace = session.get(Workspace, normalized_workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")

        existing = session.get(WorkspaceJiraSite, normalized_workspace_id)
        if existing is not None:
            if existing.cloud_id == normalized_cloud_id:
                return {"connected": True, "site": public_workspace_jira_site(existing)}
            raise ValidationError("This workspace already has a Jira site connected.")

        user_site = session.scalar(
            select(JiraUserSite).where(
                JiraUserSite.user_id == actor_user_id,
                JiraUserSite.cloud_id == normalized_cloud_id,
            )
        )
        if user_site is None:
            raise PermissionDeniedError("Connect Jira with access to this site before linking it to the workspace.")

        site = WorkspaceJiraSite(
            workspace_id=normalized_workspace_id,
            cloud_id=user_site.cloud_id,
            site_name=user_site.site_name,
            site_url=user_site.site_url,
            connected_by_user_id=actor_user_id,
        )
        session.add(site)
        session.flush()
        return {"connected": True, "site": public_workspace_jira_site(site)}


def remove_workspace_jira_site(workspace_id: str, actor_user_id: str, actor_email: str) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    normalized_workspace_id = workspace_id.strip()
    with session_scope() as session:
        site = session.get(WorkspaceJiraSite, normalized_workspace_id)
        if site is None:
            return {"connected": False, "site": None}

        public = public_workspace_jira_site(site)
        source_ids = session.scalars(
            select(WorkspaceSourceSubscription.source_id)
            .join(OrgSource, OrgSource.source_id == WorkspaceSourceSubscription.source_id)
            .where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                OrgSource.provider == "jira",
            )
        ).all()
        if source_ids:
            session.execute(
                delete(WorkspaceSourceSubscription).where(
                    WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                    WorkspaceSourceSubscription.source_id.in_(source_ids),
                )
            )
            remaining = {
                row
                for row in session.scalars(
                    select(WorkspaceSourceSubscription.source_id).where(
                        WorkspaceSourceSubscription.source_id.in_(source_ids)
                    )
                ).all()
            }
            purge_source_ids = [source_id for source_id in source_ids if source_id not in remaining]
            if purge_source_ids:
                session.execute(delete(JiraIndexedItem).where(JiraIndexedItem.source_id.in_(purge_source_ids)))
                session.execute(delete(WorkspaceJiraSource).where(WorkspaceJiraSource.source_id.in_(purge_source_ids)))
                session.execute(delete(OrgSource).where(OrgSource.source_id.in_(purge_source_ids)))
        session.delete(site)

    rebuild_workspace_jira_index(normalized_workspace_id)
    return {"connected": False, "site": public}


def list_visible_jira_projects(user_id: str, query: str = "", cloud_id: str = "") -> list[dict]:
    access_token = get_valid_jira_access_token(user_id)
    normalized_cloud_id = cloud_id.strip()
    with session_scope() as session:
        site_query = select(JiraUserSite).where(JiraUserSite.user_id == user_id)
        if normalized_cloud_id:
            site_query = site_query.where(JiraUserSite.cloud_id == normalized_cloud_id)
        site_rows = session.scalars(site_query).all()
        sites = [
            {
                "cloud_id": site.cloud_id,
                "site_name": site.site_name,
                "site_url": site.site_url,
            }
            for site in site_rows
        ]
        if not sites:
            if normalized_cloud_id:
                raise ValidationError("Connect Jira with access to this site before selecting a project.")
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
        normalized_workspace_id = workspace_id.strip()
        sources = session.scalars(
            select(OrgSource)
            .join(WorkspaceSourceSubscription, WorkspaceSourceSubscription.source_id == OrgSource.source_id)
            .where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                OrgSource.provider == "jira",
            )
            .order_by(OrgSource.created_at.desc())
        ).all()
        connected_cloud_ids = {
            site.cloud_id
            for site in session.scalars(select(JiraUserSite).where(JiraUserSite.user_id == user_id)).all()
        }
        sync_owners = {
            row.source_id: row.sync_owner_user_id
            for row in session.scalars(
                select(WorkspaceJiraSource).where(WorkspaceJiraSource.source_id.in_([source.source_id for source in sources]))
            ).all()
        }
        return [
            public_source(
                source,
                workspace_id=normalized_workspace_id,
                sync_owner_user_id=sync_owners.get(source.source_id),
                user_access=(
                    "connected"
                    if str(_parse_metadata(source.metadata_json).get("cloud_id") or "") in connected_cloud_ids
                    else "connect_jira"
                ),
            )
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
        org_id = (workspace.organization_id or workspace.workspace_id).strip()

        linked_site = session.get(WorkspaceJiraSite, workspace.workspace_id)
        if linked_site is None:
            raise ValidationError("Connect a Jira site to this workspace before adding projects.")
        if linked_site.cloud_id != cloud_id:
            raise ValidationError("Project must belong to the workspace Jira site.")

        site = session.scalar(
            select(JiraUserSite).where(
                JiraUserSite.user_id == actor_user_id,
                JiraUserSite.cloud_id == cloud_id,
            )
        )
        if site is None:
            raise PermissionDeniedError("Connect Jira with access to this site before adding the project.")
        external_key = f"{cloud_id}:{project_id}"
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.org_id == org_id,
                OrgSource.provider == "jira",
                OrgSource.external_key == external_key,
            )
        )
        if source is None:
            source = OrgSource(
                source_id=f"jira-{uuid4().hex[:16]}",
                org_id=org_id,
                provider="jira",
                external_key=external_key,
                display_name=f"{site_name} {project_key}",
                source_url=site_url,
                metadata_json=json.dumps(
                    {
                        "cloud_id": cloud_id,
                        "site_name": site_name,
                        "site_url": site_url,
                        "project_id": project_id,
                        "project_key": project_key,
                        "project_name": project_name,
                    },
                    sort_keys=True,
                ),
                added_by_user_id=actor_user_id,
                sync_owner_user_id=actor_user_id,
                next_sync_at=utc_now(),
            )
            session.add(source)
        legacy = session.get(WorkspaceJiraSource, source.source_id)
        if legacy is None:
            session.add(
                WorkspaceJiraSource(
                    source_id=source.source_id,
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
            )
        session.add(
            WorkspaceSourceSubscription(
                workspace_id=workspace.workspace_id,
                source_id=source.source_id,
                added_by_user_id=actor_user_id,
            )
        )
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("Jira project is already connected to this workspace.") from exc
        return public_source(source, workspace_id=workspace.workspace_id, user_access="connected")


def remove_workspace_jira_source(workspace_id: str, source_id: str, actor_user_id: str, actor_email: str) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.source_id == source_id.strip(),
                OrgSource.provider == "jira",
            )
        )
        subscription = session.scalar(
            select(WorkspaceSourceSubscription).where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                WorkspaceSourceSubscription.source_id == source_id.strip(),
            )
        )
        if source is None or subscription is None:
            raise ResourceNotFoundError("Jira source not found.")
        public = public_source(source, workspace_id=normalized_workspace_id, user_access="unknown")
        session.delete(subscription)
        has_remaining = session.scalar(
            select(WorkspaceSourceSubscription.subscription_id)
            .where(WorkspaceSourceSubscription.source_id == source.source_id)
            .limit(1)
        )
        if has_remaining is None:
            session.execute(delete(JiraIndexedItem).where(JiraIndexedItem.source_id == source.source_id))
            session.execute(delete(WorkspaceJiraSource).where(WorkspaceJiraSource.source_id == source.source_id))
            session.delete(source)
        return public


def require_connector_manager(user_id: str, user_email: str, workspace_id: str) -> None:
    if user_can_access_workspace(user_id, user_email, workspace_id):
        if not user_can_manage_workspace_connectors(user_id, user_email, workspace_id):
            raise PermissionDeniedError("Connector manager access required.")
        return
    normalized_email = user_email.strip().lower()
    with session_scope() as session:
        member = session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id.strip(),
                WorkspaceMember.member_email_key == normalized_email,
            )
        )
        has_manager_access = bool(member.connector_manager) if member is not None else False
    if member is None:
        raise PermissionDeniedError("Workspace access required.")
    if not has_manager_access:
        raise PermissionDeniedError("Connector manager access required.")


def _parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
