from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.backend.application.services.workspace_service import user_can_access_workspace, user_can_manage_workspace_connectors
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    ConfluenceIndexedItem,
    ConfluenceUserSite,
    OrgSource,
    Workspace,
    WorkspaceConfluenceSource,
    WorkspaceSourceSubscription,
    utc_now,
)

from .auth import get_valid_confluence_access_token
from .http import confluence_request
from .serializers import public_source


def list_visible_confluence_spaces(user_id: str, query: str = "") -> list[dict]:
    token = get_valid_confluence_access_token(user_id)
    with session_scope() as session:
        sites = session.scalars(select(ConfluenceUserSite).where(ConfluenceUserSite.user_id == user_id)).all()
        site_rows = [{"cloud_id": site.cloud_id, "site_name": site.site_name, "site_url": site.site_url} for site in sites]
    spaces: list[dict] = []
    for site in site_rows:
        data = confluence_request(site["cloud_id"], "/wiki/api/v2/spaces", token, query={"limit": "100"})
        for space in data.get("results", []) if isinstance(data, dict) else []:
            space_id = str(space.get("id") or space.get("key") or "")
            space_key = str(space.get("key") or "")
            space_name = str(space.get("name") or "")
            if not space_id or not space_key or not space_name:
                continue
            row = {**site, "space_id": space_id, "space_key": space_key, "space_name": space_name}
            if not query.strip() or query.strip().lower() in f"{space_key} {space_name}".lower():
                spaces.append(row)
    return spaces


def list_workspace_confluence_sources(workspace_id: str, user_id: str) -> list[dict]:
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        sources = session.scalars(
            select(OrgSource)
            .join(WorkspaceSourceSubscription, WorkspaceSourceSubscription.source_id == OrgSource.source_id)
            .where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                OrgSource.provider == "confluence",
            )
            .order_by(OrgSource.created_at.desc())
        ).all()
        connected_clouds = {site.cloud_id for site in session.scalars(select(ConfluenceUserSite).where(ConfluenceUserSite.user_id == user_id)).all()}
        sync_owners = {
            row.source_id: row.sync_owner_user_id
            for row in session.scalars(
                select(WorkspaceConfluenceSource).where(WorkspaceConfluenceSource.source_id.in_([source.source_id for source in sources]))
            ).all()
        }
        return [
            public_source(
                source,
                workspace_id=normalized_workspace_id,
                sync_owner_user_id=sync_owners.get(source.source_id),
                user_access=(
                    "connected"
                    if str(_parse_metadata(source.metadata_json).get("cloud_id") or "") in connected_clouds
                    else "connect_confluence"
                ),
            )
            for source in sources
        ]


def add_workspace_confluence_source(workspace_id: str, actor_user_id: str, actor_email: str, payload: dict) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    cloud_id = required_payload(payload, "cloud_id")
    space_id = required_payload(payload, "space_id")
    space_key = required_payload(payload, "space_key")
    space_name = required_payload(payload, "space_name")
    site_name = required_payload(payload, "site_name")
    site_url = required_payload(payload, "site_url")
    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id.strip())
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        org_id = (workspace.organization_id or workspace.workspace_id).strip()
        site = session.scalar(select(ConfluenceUserSite).where(ConfluenceUserSite.user_id == actor_user_id, ConfluenceUserSite.cloud_id == cloud_id))
        if site is None:
            raise PermissionDeniedError("Connect Confluence with access to this site before adding the space.")
        external_key = f"{cloud_id}:{space_id}"
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.org_id == org_id,
                OrgSource.provider == "confluence",
                OrgSource.external_key == external_key,
            )
        )
        if source is None:
            source = OrgSource(
                source_id=f"confluence-{uuid4().hex[:16]}",
                org_id=org_id,
                provider="confluence",
                external_key=external_key,
                display_name=f"{site_name} {space_key}",
                source_url=site_url,
                metadata_json=json.dumps(
                    {
                        "cloud_id": cloud_id,
                        "site_name": site_name,
                        "site_url": site_url,
                        "space_id": space_id,
                        "space_key": space_key,
                        "space_name": space_name,
                    },
                    sort_keys=True,
                ),
                added_by_user_id=actor_user_id,
                sync_owner_user_id=actor_user_id,
                next_sync_at=utc_now(),
            )
            session.add(source)
        legacy = session.get(WorkspaceConfluenceSource, source.source_id)
        if legacy is None:
            session.add(
                WorkspaceConfluenceSource(
                    source_id=source.source_id,
                    workspace_id=workspace.workspace_id,
                    cloud_id=cloud_id,
                    site_name=site_name,
                    site_url=site_url,
                    space_id=space_id,
                    space_key=space_key,
                    space_name=space_name,
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
            raise ValidationError("Confluence space is already connected to this workspace.") from exc
        return public_source(source, workspace_id=workspace.workspace_id, user_access="connected")


def remove_workspace_confluence_source(workspace_id: str, source_id: str, actor_user_id: str, actor_email: str) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.source_id == source_id.strip(),
                OrgSource.provider == "confluence",
            )
        )
        subscription = session.scalar(
            select(WorkspaceSourceSubscription).where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                WorkspaceSourceSubscription.source_id == source_id.strip(),
            )
        )
        if source is None or subscription is None:
            raise ResourceNotFoundError("Confluence source not found.")
        public = public_source(source, workspace_id=normalized_workspace_id, user_access="unknown")
        session.delete(subscription)
        has_remaining = session.scalar(
            select(WorkspaceSourceSubscription.subscription_id)
            .where(WorkspaceSourceSubscription.source_id == source.source_id)
            .limit(1)
        )
        if has_remaining is None:
            session.execute(delete(ConfluenceIndexedItem).where(ConfluenceIndexedItem.source_id == source.source_id))
            session.execute(delete(WorkspaceConfluenceSource).where(WorkspaceConfluenceSource.source_id == source.source_id))
            session.delete(source)
        return public


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


def _parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
