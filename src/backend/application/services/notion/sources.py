from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.backend.application.services.workspace_service import user_can_access_workspace, user_can_manage_workspace_connectors
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    NotionIndexedItem,
    NotionUserConnection,
    OrgSource,
    Workspace,
    WorkspaceNotionSource,
    WorkspaceSourceSubscription,
    utc_now,
)

from .auth import get_valid_notion_access_token
from .http import notion_request
from .serializers import public_source


def list_visible_notion_databases(user_id: str, query: str = "") -> list[dict]:
    token = get_valid_notion_access_token(user_id)
    with session_scope() as session:
        connection = session.scalar(select(NotionUserConnection).where(NotionUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Notion before searching databases.")
        notion_workspace_id = connection.notion_workspace_id or ""
        workspace_name = connection.workspace_name or "Notion workspace"

    databases: list[dict] = []
    start_cursor: str | None = None
    while len(databases) < 100:
        body: dict = {
            "filter": {"value": "database", "property": "object"},
            "page_size": min(100, 100 - len(databases)),
        }
        if query.strip():
            body["query"] = query.strip()
        if start_cursor:
            body["start_cursor"] = start_cursor
        data = notion_request("/search", token, method="POST", body=body)
        for result in data.get("results", []) if isinstance(data, dict) else []:
            if not isinstance(result, dict) or result.get("object") != "database":
                continue
            database_id = str(result.get("id") or "")
            database_title = database_title_from(result)
            if not database_id or not database_title:
                continue
            row = {
                "notion_workspace_id": notion_workspace_id,
                "workspace_name": workspace_name,
                "database_id": database_id,
                "database_title": database_title,
            }
            if not query.strip() or query.strip().lower() in database_title.lower():
                databases.append(row)
        if not data.get("has_more"):
            break
        start_cursor = str(data.get("next_cursor") or "") or None
        if not start_cursor:
            break
    return databases


def list_workspace_notion_sources(workspace_id: str, user_id: str) -> list[dict]:
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        sources = session.scalars(
            select(OrgSource)
            .join(WorkspaceSourceSubscription, WorkspaceSourceSubscription.source_id == OrgSource.source_id)
            .where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                OrgSource.provider == "notion",
            )
            .order_by(OrgSource.created_at.desc())
        ).all()
        connected = session.scalar(select(NotionUserConnection).where(NotionUserConnection.user_id == user_id)) is not None
        access = "connected" if connected else "connect_notion"
        sync_owners = {
            row.source_id: row.sync_owner_user_id
            for row in session.scalars(
                select(WorkspaceNotionSource).where(WorkspaceNotionSource.source_id.in_([source.source_id for source in sources]))
            ).all()
        }
        return [
            public_source(
                source,
                workspace_id=normalized_workspace_id,
                sync_owner_user_id=sync_owners.get(source.source_id),
                user_access=access,
            )
            for source in sources
        ]


def add_workspace_notion_source(workspace_id: str, actor_user_id: str, actor_email: str, payload: dict) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    notion_workspace_id = required_payload(payload, "notion_workspace_id")
    database_id = required_payload(payload, "database_id")
    database_title = required_payload(payload, "database_title")
    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id.strip())
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        org_id = (workspace.organization_id or workspace.workspace_id).strip()
        connection = session.scalar(select(NotionUserConnection).where(NotionUserConnection.user_id == actor_user_id))
        if connection is None or (connection.notion_workspace_id and connection.notion_workspace_id != notion_workspace_id):
            raise PermissionDeniedError("Connect Notion with access to this workspace before adding the database.")
        external_key = f"{notion_workspace_id}:{database_id}"
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.org_id == org_id,
                OrgSource.provider == "notion",
                OrgSource.external_key == external_key,
            )
        )
        if source is None:
            source = OrgSource(
                source_id=f"notion-{uuid4().hex[:16]}",
                org_id=org_id,
                provider="notion",
                external_key=external_key,
                display_name=database_title,
                source_url=None,
                metadata_json=json.dumps(
                    {
                        "notion_workspace_id": notion_workspace_id,
                        "database_id": database_id,
                        "database_title": database_title,
                    },
                    sort_keys=True,
                ),
                added_by_user_id=actor_user_id,
                sync_owner_user_id=actor_user_id,
                next_sync_at=utc_now(),
            )
            session.add(source)
        legacy = session.get(WorkspaceNotionSource, source.source_id)
        if legacy is None:
            session.add(
                WorkspaceNotionSource(
                    source_id=source.source_id,
                    workspace_id=workspace.workspace_id,
                    notion_workspace_id=notion_workspace_id,
                    database_id=database_id,
                    database_title=database_title,
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
            raise ValidationError("Notion database is already connected to this workspace.") from exc
        return public_source(source, workspace_id=workspace.workspace_id, user_access="connected")


def remove_workspace_notion_source(workspace_id: str, source_id: str, actor_user_id: str, actor_email: str) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.source_id == source_id.strip(),
                OrgSource.provider == "notion",
            )
        )
        subscription = session.scalar(
            select(WorkspaceSourceSubscription).where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                WorkspaceSourceSubscription.source_id == source_id.strip(),
            )
        )
        if source is None or subscription is None:
            raise ResourceNotFoundError("Notion source not found.")
        public = public_source(source, workspace_id=normalized_workspace_id, user_access="unknown")
        session.delete(subscription)
        has_remaining = session.scalar(
            select(WorkspaceSourceSubscription.subscription_id)
            .where(WorkspaceSourceSubscription.source_id == source.source_id)
            .limit(1)
        )
        if has_remaining is None:
            session.execute(delete(NotionIndexedItem).where(NotionIndexedItem.source_id == source.source_id))
            session.execute(delete(WorkspaceNotionSource).where(WorkspaceNotionSource.source_id == source.source_id))
            session.delete(source)
        return public


def database_title_from(database: dict) -> str:
    title = database.get("title")
    if isinstance(title, list):
        parts = [str(item.get("plain_text") or "") for item in title if isinstance(item, dict)]
        text = "".join(parts).strip()
        if text:
            return text
    return str(database.get("id") or "Untitled database")


def require_connector_manager(user_id: str, user_email: str, workspace_id: str) -> None:
    if not user_can_access_workspace(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Workspace access required.")
    if not user_can_manage_workspace_connectors(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Connector manager access required.")


def required_payload(payload: dict, key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValidationError(f"{key} is required.")
    return value
