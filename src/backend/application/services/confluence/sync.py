from __future__ import annotations

import json
import threading
import time
from datetime import timedelta

from sqlalchemy import or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    ConfluenceIndexedItem,
    ConfluenceUserSite,
    OrgSource,
    WorkspaceConfluenceSource,
    WorkspaceMember,
    WorkspaceSourceSubscription,
    utc_now,
)
from src.backend.infrastructure.retrieval.retriever import build_confluence_index

from .auth import get_valid_confluence_access_token
from .constants import CONFLUENCE_SYNC_INTERVAL_SECONDS, CONFLUENCE_SYNC_LIMIT, CONFLUENCE_SYNC_SCHEDULER_DISABLED
from .http import confluence_request
from .normalize import normalize_pages
from .serializers import public_source

_scheduler_started = False


def sync_workspace_confluence_source(source_id: str, workspace_id: str | None = None) -> dict:
    if workspace_id is not None:
        require_workspace_subscription(source_id, workspace_id)
    mark_source_syncing(source_id)
    try:
        owner_user_id = select_sync_owner(source_id)
        source = get_source(source_id)
        token = get_valid_confluence_access_token(owner_user_id)
        pages = fetch_pages(source, token)
        items = normalize_pages(source, pages)
        upsert_indexed_items(items)
        rebuild_subscribed_workspace_indexes(source_id)
        update_source_success(source_id, owner_user_id)
    except Exception as exc:
        return update_source_failure(source_id, exc)
    return get_source(source_id)


def sync_due_confluence_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(OrgSource)
            .where(
                OrgSource.provider == "confluence",
                OrgSource.sync_status != "syncing",
                or_(OrgSource.next_sync_at.is_(None), OrgSource.next_sync_at <= now),
            )
            .order_by(OrgSource.next_sync_at.asc())
            .limit(limit)
        ).all()
        source_ids = [source.source_id for source in sources]
    return [sync_workspace_confluence_source(source_id) for source_id in source_ids]


def start_confluence_sync_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started or CONFLUENCE_SYNC_SCHEDULER_DISABLED:
        return
    _scheduler_started = True

    def run() -> None:
        while True:
            try:
                sync_due_confluence_sources()
            except Exception:
                pass
            time.sleep(max(60, CONFLUENCE_SYNC_INTERVAL_SECONDS))

    threading.Thread(target=run, name="readbase-confluence-sync", daemon=True).start()


def fetch_pages(source: dict, token: str) -> list[dict]:
    data = confluence_request(
        source["cloud_id"],
        f"/wiki/api/v2/spaces/{source['space_id']}/pages",
        token,
        query={
            "limit": str(CONFLUENCE_SYNC_LIMIT),
            "body-format": "storage",
        },
    )
    return [page for page in data.get("results", []) if isinstance(page, dict)] if isinstance(data, dict) else []


def upsert_indexed_items(items: list[dict]) -> None:
    with session_scope() as session:
        for item in items:
            existing = session.scalar(
                select(ConfluenceIndexedItem).where(
                    ConfluenceIndexedItem.source_id == item["source_id"],
                    ConfluenceIndexedItem.item_type == item["item_type"],
                    ConfluenceIndexedItem.item_id == item["item_id"],
                )
            )
            if existing is None:
                session.add(ConfluenceIndexedItem(**item))
                continue
            for key, value in item.items():
                setattr(existing, key, value)


def rebuild_workspace_confluence_index(workspace_id: str) -> None:
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        source_ids = [
            row.source_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription.source_id)
                .join(OrgSource, OrgSource.source_id == WorkspaceSourceSubscription.source_id)
                .where(
                    WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                    OrgSource.provider == "confluence",
                )
            ).all()
        ]
        if not source_ids:
            build_confluence_index([], normalized_workspace_id)
            return
        rows = session.scalars(select(ConfluenceIndexedItem).where(ConfluenceIndexedItem.source_id.in_(source_ids))).all()
        unique_rows: dict[str, ConfluenceIndexedItem] = {}
        for row in rows:
            existing = unique_rows.get(row.page_id)
            if existing is None or row.indexed_at > existing.indexed_at:
                unique_rows[row.page_id] = row
        chunks = [
            {
                "id": f"confluence:{normalized_workspace_id}:{row.item_type}:{row.item_id}",
                "path": f"confluence/{row.space_key}/{row.page_id}",
                "text": f"{row.title}\n\n{row.body}",
                "source_url": row.source_url,
                "cloud_id": row.cloud_id,
                "space_id": row.space_id,
                "space_key": row.space_key,
                "page_id": row.page_id,
                "item_type": row.item_type,
                "item_id": row.item_id,
            }
            for row in unique_rows.values()
        ]
    build_confluence_index(chunks, normalized_workspace_id)


def select_sync_owner(source_id: str) -> str:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "confluence":
            raise ResourceNotFoundError("Confluence source not found.")
        metadata = parse_metadata(source.metadata_json)
        workspace_ids = [
            row.workspace_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription).where(WorkspaceSourceSubscription.source_id == source_id)
            ).all()
        ]
        candidates = [source.sync_owner_user_id, source.added_by_user_id]
        for workspace_id in workspace_ids:
            members = session.scalars(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.connector_manager.is_(True),
                )
            ).all()
            candidates.extend(member.user_id for member in members if member.user_id)
        for candidate in dict.fromkeys(candidates):
            if candidate and session.scalar(
                select(ConfluenceUserSite).where(
                    ConfluenceUserSite.user_id == candidate,
                    ConfluenceUserSite.cloud_id == str(metadata.get("cloud_id") or ""),
                )
            ):
                return candidate
    raise PermissionDeniedError("No connected Confluence user can sync this source.")


def mark_source_syncing(source_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id.strip())
        if source is None or source.provider != "confluence":
            raise ResourceNotFoundError("Confluence source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()


def update_source_success(source_id: str, owner_user_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "confluence":
            raise ResourceNotFoundError("Confluence source not found.")
        source.sync_owner_user_id = owner_user_id
        source.sync_status = "synced"
        source.sync_error = None
        source.last_synced_at = utc_now()
        source.next_sync_at = utc_now() + timedelta(seconds=CONFLUENCE_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy = session.get(WorkspaceConfluenceSource, source_id)
        if legacy is not None:
            legacy.sync_owner_user_id = owner_user_id
            legacy.sync_status = source.sync_status
            legacy.sync_error = None
            legacy.last_synced_at = source.last_synced_at
            legacy.next_sync_at = source.next_sync_at
            legacy.updated_at = source.updated_at


def update_source_failure(source_id: str, exc: Exception) -> dict:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "confluence":
            raise ResourceNotFoundError("Confluence source not found.")
        source.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
        source.sync_error = str(exc)[:1000]
        source.next_sync_at = utc_now() + timedelta(seconds=CONFLUENCE_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy = session.get(WorkspaceConfluenceSource, source_id)
        if legacy is not None:
            legacy.sync_status = source.sync_status
            legacy.sync_error = source.sync_error
            legacy.next_sync_at = source.next_sync_at
            legacy.updated_at = source.updated_at
        workspace_id = session.scalar(
            select(WorkspaceSourceSubscription.workspace_id)
            .where(WorkspaceSourceSubscription.source_id == source_id)
            .limit(1)
        )
        return public_source(source, workspace_id=workspace_id or "", user_access="unknown")


def get_source(source_id: str) -> dict:
    with session_scope() as session:
        source = session.get(OrgSource, source_id.strip())
        if source is None or source.provider != "confluence":
            raise ResourceNotFoundError("Confluence source not found.")
        metadata = parse_metadata(source.metadata_json)
        workspace_id = session.scalar(
            select(WorkspaceSourceSubscription.workspace_id)
            .where(WorkspaceSourceSubscription.source_id == source.source_id)
            .limit(1)
        )
        sync_owner_user_id = session.scalar(
            select(WorkspaceConfluenceSource.sync_owner_user_id)
            .where(WorkspaceConfluenceSource.source_id == source.source_id)
            .limit(1)
        )
        payload = public_source(
            source,
            workspace_id=workspace_id or "",
            sync_owner_user_id=sync_owner_user_id,
            user_access="unknown",
        )
        payload["cloud_id"] = str(metadata.get("cloud_id") or "")
        payload["site_name"] = str(metadata.get("site_name") or "")
        payload["site_url"] = str(metadata.get("site_url") or "")
        payload["space_id"] = str(metadata.get("space_id") or "")
        payload["space_key"] = str(metadata.get("space_key") or "")
        payload["space_name"] = str(metadata.get("space_name") or "")
        payload["org_id"] = source.org_id
        return payload


def require_workspace_subscription(source_id: str, workspace_id: str) -> None:
    with session_scope() as session:
        subscription = session.scalar(
            select(WorkspaceSourceSubscription).where(
                WorkspaceSourceSubscription.workspace_id == workspace_id.strip(),
                WorkspaceSourceSubscription.source_id == source_id.strip(),
            )
        )
        if subscription is None:
            raise ResourceNotFoundError("Confluence source not found.")


def rebuild_subscribed_workspace_indexes(source_id: str) -> None:
    with session_scope() as session:
        workspace_ids = [
            row.workspace_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription).where(WorkspaceSourceSubscription.source_id == source_id)
            ).all()
        ]
    for workspace_id in workspace_ids:
        rebuild_workspace_confluence_index(workspace_id)


def parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
