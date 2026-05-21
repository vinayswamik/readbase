from __future__ import annotations

import threading
import time
from datetime import timedelta

from sqlalchemy import or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import ConfluenceIndexedItem, ConfluenceUserSite, WorkspaceConfluenceSource, WorkspaceMember, utc_now
from src.backend.infrastructure.retrieval.retriever import build_confluence_index

from .auth import get_valid_confluence_access_token
from .constants import CONFLUENCE_SYNC_INTERVAL_SECONDS, CONFLUENCE_SYNC_LIMIT, CONFLUENCE_SYNC_SCHEDULER_DISABLED
from .http import confluence_request
from .normalize import normalize_pages
from .serializers import public_source

_scheduler_started = False


def sync_workspace_confluence_source(source_id: str, workspace_id: str | None = None) -> dict:
    mark_source_syncing(source_id, workspace_id)
    try:
        owner_user_id = select_sync_owner(source_id)
        source = get_source_row(source_id)
        token = get_valid_confluence_access_token(owner_user_id)
        pages = fetch_pages(source, token)
        items = normalize_pages(source, pages)
        upsert_indexed_items(items)
        rebuild_workspace_confluence_index(source.workspace_id)
        update_source_success(source_id, owner_user_id)
    except Exception as exc:
        return update_source_failure(source_id, exc)
    return get_source(source_id)


def sync_due_confluence_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(WorkspaceConfluenceSource)
            .where(WorkspaceConfluenceSource.sync_status != "syncing", or_(WorkspaceConfluenceSource.next_sync_at.is_(None), WorkspaceConfluenceSource.next_sync_at <= now))
            .order_by(WorkspaceConfluenceSource.next_sync_at.asc())
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


def fetch_pages(source: WorkspaceConfluenceSource, token: str) -> list[dict]:
    data = confluence_request(
        source.cloud_id,
        f"/wiki/api/v2/spaces/{source.space_id}/pages",
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
        rows = session.scalars(select(ConfluenceIndexedItem).where(ConfluenceIndexedItem.workspace_id == workspace_id)).all()
        chunks = [
            {
                "id": f"confluence:{row.source_id}:{row.item_type}:{row.item_id}",
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
            for row in rows
        ]
    build_confluence_index(chunks, workspace_id)


def select_sync_owner(source_id: str) -> str:
    with session_scope() as session:
        source = session.get(WorkspaceConfluenceSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Confluence source not found.")
        candidates = [source.sync_owner_user_id]
        members = session.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == source.workspace_id, WorkspaceMember.connector_manager.is_(True))).all()
        candidates.extend(member.user_id for member in members if member.user_id)
        for candidate in dict.fromkeys(candidates):
            if candidate and session.scalar(select(ConfluenceUserSite).where(ConfluenceUserSite.user_id == candidate, ConfluenceUserSite.cloud_id == source.cloud_id)):
                return candidate
    raise PermissionDeniedError("No connected Confluence user can sync this source.")


def mark_source_syncing(source_id: str, workspace_id: str | None) -> None:
    with session_scope() as session:
        source = session.get(WorkspaceConfluenceSource, source_id.strip())
        if source is None or (workspace_id is not None and source.workspace_id != workspace_id.strip()):
            raise ResourceNotFoundError("Confluence source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()


def update_source_success(source_id: str, owner_user_id: str) -> None:
    with session_scope() as session:
        source = session.get(WorkspaceConfluenceSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Confluence source not found.")
        source.sync_owner_user_id = owner_user_id
        source.sync_status = "synced"
        source.sync_error = None
        source.last_synced_at = utc_now()
        source.next_sync_at = utc_now() + timedelta(seconds=CONFLUENCE_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()


def update_source_failure(source_id: str, exc: Exception) -> dict:
    with session_scope() as session:
        source = session.get(WorkspaceConfluenceSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Confluence source not found.")
        source.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
        source.sync_error = str(exc)[:1000]
        source.next_sync_at = utc_now() + timedelta(seconds=CONFLUENCE_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        return public_source(source, user_access="unknown")


def get_source(source_id: str) -> dict:
    return public_source(get_source_row(source_id), user_access="unknown")


def get_source_row(source_id: str) -> WorkspaceConfluenceSource:
    with session_scope() as session:
        source = session.get(WorkspaceConfluenceSource, source_id.strip())
        if source is None:
            raise ResourceNotFoundError("Confluence source not found.")
        session.expunge(source)
        return source
