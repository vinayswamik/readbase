from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.backend.application.services.workspace_service import user_can_access_workspace, user_can_manage_workspace_connectors
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    LinearIndexedItem,
    LinearUserConnection,
    OrgSource,
    Workspace,
    WorkspaceLinearSource,
    WorkspaceSourceSubscription,
    utc_now,
)

from .auth import get_valid_linear_access_token
from .http import linear_graphql_request
from .serializers import public_source


def list_visible_linear_sources(user_id: str, query: str = "") -> list[dict]:
    token = get_valid_linear_access_token(user_id)
    data = linear_graphql_request(
        """
        query {
          teams(first: 100) { nodes { id name key } }
          projects(first: 100) { nodes { id name url teams(first: 20) { nodes { id name key } } } }
        }
        """,
        token,
    )
    normalized = query.strip().lower()
    rows: list[dict] = []
    for team in nodes(data.get("teams")):
        item = {"kind": "team", "team_id": team.get("id", ""), "team_name": team.get("name", ""), "project_id": None, "project_name": None}
        if matches(item, normalized):
            rows.append(item)
    for project in nodes(data.get("projects")):
        for team in nodes(project.get("teams")) or [{}]:
            item = {
                "kind": "project",
                "team_id": team.get("id", ""),
                "team_name": team.get("name", ""),
                "project_id": project.get("id", ""),
                "project_name": project.get("name", ""),
            }
            if item["team_id"] and matches(item, normalized):
                rows.append(item)
    return rows


def list_workspace_linear_sources(workspace_id: str, user_id: str) -> list[dict]:
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        sources = session.scalars(
            select(OrgSource)
            .join(WorkspaceSourceSubscription, WorkspaceSourceSubscription.source_id == OrgSource.source_id)
            .where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                OrgSource.provider == "linear",
            )
            .order_by(OrgSource.created_at.desc())
        ).all()
        connected = session.scalar(select(LinearUserConnection).where(LinearUserConnection.user_id == user_id)) is not None
        sync_owners = {
            row.source_id: row.sync_owner_user_id
            for row in session.scalars(
                select(WorkspaceLinearSource).where(WorkspaceLinearSource.source_id.in_([source.source_id for source in sources]))
            ).all()
        }
        return [
            public_source(
                source,
                workspace_id=normalized_workspace_id,
                sync_owner_user_id=sync_owners.get(source.source_id),
                user_access=("connected" if connected else "connect_linear"),
            )
            for source in sources
        ]


def add_workspace_linear_source(workspace_id: str, actor_user_id: str, actor_email: str, payload: dict) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    team_id = required_payload(payload, "team_id")
    team_name = required_payload(payload, "team_name")
    project_id = optional_payload(payload, "project_id")
    project_name = optional_payload(payload, "project_name")
    get_valid_linear_access_token(actor_user_id)
    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id.strip())
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        org_id = (workspace.organization_id or workspace.workspace_id).strip()
        external_key = f"{team_id}:{project_id or ''}"
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.org_id == org_id,
                OrgSource.provider == "linear",
                OrgSource.external_key == external_key,
            )
        )
        if source is None:
            source = OrgSource(
                source_id=f"linear-{uuid4().hex[:16]}",
                org_id=org_id,
                provider="linear",
                external_key=external_key,
                display_name=f"{team_name} / {project_name or 'all issues'}",
                source_url=None,
                metadata_json=json.dumps(
                    {
                        "linear_team_id": team_id,
                        "team_name": team_name,
                        "linear_project_id": project_id,
                        "project_name": project_name,
                    },
                    sort_keys=True,
                ),
                added_by_user_id=actor_user_id,
                sync_owner_user_id=actor_user_id,
                next_sync_at=utc_now(),
            )
            session.add(source)
        legacy = session.get(WorkspaceLinearSource, source.source_id)
        if legacy is None:
            session.add(
                WorkspaceLinearSource(
                    source_id=source.source_id,
                    workspace_id=workspace.workspace_id,
                    linear_team_id=team_id,
                    team_name=team_name,
                    linear_project_id=project_id,
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
            raise ValidationError("Linear source is already connected to this workspace.") from exc
        return public_source(source, workspace_id=workspace.workspace_id, user_access="connected")


def remove_workspace_linear_source(workspace_id: str, source_id: str, actor_user_id: str, actor_email: str) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.source_id == source_id.strip(),
                OrgSource.provider == "linear",
            )
        )
        subscription = session.scalar(
            select(WorkspaceSourceSubscription).where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                WorkspaceSourceSubscription.source_id == source_id.strip(),
            )
        )
        if source is None or subscription is None:
            raise ResourceNotFoundError("Linear source not found.")
        public = public_source(source, workspace_id=normalized_workspace_id, user_access="unknown")
        session.delete(subscription)
        has_remaining = session.scalar(
            select(WorkspaceSourceSubscription.subscription_id)
            .where(WorkspaceSourceSubscription.source_id == source.source_id)
            .limit(1)
        )
        if has_remaining is None:
            session.execute(delete(LinearIndexedItem).where(LinearIndexedItem.source_id == source.source_id))
            session.execute(delete(WorkspaceLinearSource).where(WorkspaceLinearSource.source_id == source.source_id))
            session.delete(source)
        return public


def require_connector_manager(user_id: str, user_email: str, workspace_id: str) -> None:
    if not user_can_access_workspace(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Workspace access required.")
    if not user_can_manage_workspace_connectors(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Connector manager access required.")


def nodes(value: object) -> list[dict]:
    if isinstance(value, dict) and isinstance(value.get("nodes"), list):
        return [node for node in value["nodes"] if isinstance(node, dict)]
    return []


def matches(item: dict, query: str) -> bool:
    if not query:
        return True
    return query in " ".join(str(item.get(key) or "").lower() for key in item).lower()


def required_payload(payload: dict, key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValidationError(f"{key} is required.")
    return value


def optional_payload(payload: dict, key: str) -> str | None:
    value = str(payload.get(key) or "").strip()
    return value or None
