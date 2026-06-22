from __future__ import annotations

import json
import threading
import time
from datetime import timedelta

from sqlalchemy import or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    NotionIndexedItem,
    NotionUserConnection,
    OrgSource,
    WorkspaceMember,
    WorkspaceNotionSource,
    WorkspaceSourceSubscription,
    utc_now,
)
from src.backend.infrastructure.retrieval.retriever import build_notion_index

from .auth import get_valid_notion_access_token
from .constants import NOTION_SYNC_INTERVAL_SECONDS, NOTION_SYNC_LIMIT, NOTION_SYNC_SCHEDULER_DISABLED
from .http import notion_request
from .normalize import blocks_to_text, normalize_pages
from .serializers import public_source

_scheduler_started = False


def sync_workspace_notion_source(source_id: str, workspace_id: str | None = None) -> dict:
    if workspace_id is not None:
        require_workspace_subscription(source_id, workspace_id)
    mark_source_syncing(source_id)
    try:
        owner_user_id = select_sync_owner(source_id)
        source = get_source(source_id)
        token = get_valid_notion_access_token(owner_user_id)
        pages = fetch_database_pages(source, token)
        bodies = {page_id: fetch_page_body(page_id, token) for page_id in [str(page.get("id") or "") for page in pages] if page.get("id")}
        items = normalize_pages(source, pages, bodies)
        upsert_indexed_items(items)
        rebuild_subscribed_workspace_indexes(source_id)
        update_source_success(source_id, owner_user_id)
    except Exception as exc:
        return update_source_failure(source_id, exc)
    return get_source(source_id)


def sync_due_notion_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(OrgSource)
            .where(
                OrgSource.provider == "notion",
                OrgSource.sync_status != "syncing",
                or_(OrgSource.next_sync_at.is_(None), OrgSource.next_sync_at <= now),
            )
            .order_by(OrgSource.next_sync_at.asc())
            .limit(limit)
        ).all()
        source_ids = [source.source_id for source in sources]
    return [sync_workspace_notion_source(source_id) for source_id in source_ids]


def start_notion_sync_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started or NOTION_SYNC_SCHEDULER_DISABLED:
        return
    _scheduler_started = True

    def run() -> None:
        while True:
            try:
                sync_due_notion_sources()
            except Exception:
                pass
            time.sleep(max(60, NOTION_SYNC_INTERVAL_SECONDS))

    threading.Thread(target=run, name="readbase-notion-sync", daemon=True).start()


def fetch_database_pages(source: dict, token: str) -> list[dict]:
    pages: list[dict] = []
    start_cursor: str | None = None
    while len(pages) < NOTION_SYNC_LIMIT:
        body: dict = {"page_size": min(100, NOTION_SYNC_LIMIT - len(pages))}
        if start_cursor:
            body["start_cursor"] = start_cursor
        data = notion_request(f"/databases/{source['database_id']}/query", token, method="POST", body=body)
        batch = [page for page in data.get("results", []) if isinstance(page, dict)]
        pages.extend(batch)
        if not data.get("has_more") or len(pages) >= NOTION_SYNC_LIMIT:
            break
        start_cursor = str(data.get("next_cursor") or "") or None
        if not start_cursor:
            break
    return pages


def fetch_page_body(page_id: str, token: str) -> str:
    blocks = fetch_block_children(page_id, token)
    return blocks_to_text(blocks)


def fetch_block_children(block_id: str, token: str) -> list[dict]:
    blocks: list[dict] = []
    start_cursor: str | None = None
    while len(blocks) < 200:
        query = {"page_size": "100"}
        if start_cursor:
            query["start_cursor"] = start_cursor
        data = notion_request(f"/blocks/{block_id}/children", token, query=query)
        blocks.extend([block for block in data.get("results", []) if isinstance(block, dict)])
        if not data.get("has_more"):
            break
        start_cursor = str(data.get("next_cursor") or "") or None
        if not start_cursor:
            break
    return blocks


def upsert_indexed_items(items: list[dict]) -> None:
    with session_scope() as session:
        for item in items:
            existing = session.scalar(
                select(NotionIndexedItem).where(
                    NotionIndexedItem.source_id == item["source_id"],
                    NotionIndexedItem.item_type == item["item_type"],
                    NotionIndexedItem.item_id == item["item_id"],
                )
            )
            if existing is None:
                session.add(NotionIndexedItem(**item))
                continue
            for key, value in item.items():
                setattr(existing, key, value)


def rebuild_workspace_notion_index(workspace_id: str) -> None:
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        source_ids = [
            row.source_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription.source_id)
                .join(OrgSource, OrgSource.source_id == WorkspaceSourceSubscription.source_id)
                .where(
                    WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                    OrgSource.provider == "notion",
                )
            ).all()
        ]
        if not source_ids:
            build_notion_index([], normalized_workspace_id)
            return
        rows = session.scalars(select(NotionIndexedItem).where(NotionIndexedItem.source_id.in_(source_ids))).all()
        unique_rows: dict[str, NotionIndexedItem] = {}
        for row in rows:
            existing = unique_rows.get(row.page_id)
            if existing is None or row.indexed_at > existing.indexed_at:
                unique_rows[row.page_id] = row
        chunks = [
            {
                "id": f"notion:{normalized_workspace_id}:{row.item_type}:{row.item_id}",
                "path": f"notion/{row.database_id}/{row.page_id}",
                "text": f"{row.title}\n\n{row.body}",
                "source_url": row.source_url,
                "notion_workspace_id": row.notion_workspace_id,
                "database_id": row.database_id,
                "page_id": row.page_id,
                "item_type": row.item_type,
                "item_id": row.item_id,
            }
            for row in unique_rows.values()
        ]
    build_notion_index(chunks, normalized_workspace_id)


def select_sync_owner(source_id: str) -> str:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "notion":
            raise ResourceNotFoundError("Notion source not found.")
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
            if candidate and session.scalar(select(NotionUserConnection).where(NotionUserConnection.user_id == candidate)):
                return candidate
    raise PermissionDeniedError("No connected Notion user can sync this source.")


def mark_source_syncing(source_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id.strip())
        if source is None or source.provider != "notion":
            raise ResourceNotFoundError("Notion source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()


def update_source_success(source_id: str, owner_user_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "notion":
            raise ResourceNotFoundError("Notion source not found.")
        source.sync_owner_user_id = owner_user_id
        source.sync_status = "synced"
        source.sync_error = None
        source.last_synced_at = utc_now()
        source.next_sync_at = utc_now() + timedelta(seconds=NOTION_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy = session.get(WorkspaceNotionSource, source_id)
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
        if source is None or source.provider != "notion":
            raise ResourceNotFoundError("Notion source not found.")
        source.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
        source.sync_error = str(exc)[:1000]
        source.next_sync_at = utc_now() + timedelta(seconds=NOTION_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy = session.get(WorkspaceNotionSource, source_id)
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
        if source is None or source.provider != "notion":
            raise ResourceNotFoundError("Notion source not found.")
        metadata = parse_metadata(source.metadata_json)
        workspace_id = session.scalar(
            select(WorkspaceSourceSubscription.workspace_id)
            .where(WorkspaceSourceSubscription.source_id == source.source_id)
            .limit(1)
        )
        sync_owner_user_id = session.scalar(
            select(WorkspaceNotionSource.sync_owner_user_id)
            .where(WorkspaceNotionSource.source_id == source.source_id)
            .limit(1)
        )
        payload = public_source(
            source,
            workspace_id=workspace_id or "",
            sync_owner_user_id=sync_owner_user_id,
            user_access="unknown",
        )
        payload["notion_workspace_id"] = str(metadata.get("notion_workspace_id") or "")
        payload["database_id"] = str(metadata.get("database_id") or "")
        payload["database_title"] = str(metadata.get("database_title") or "")
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
            raise ResourceNotFoundError("Notion source not found.")


def rebuild_subscribed_workspace_indexes(source_id: str) -> None:
    with session_scope() as session:
        workspace_ids = [
            row.workspace_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription).where(WorkspaceSourceSubscription.source_id == source_id)
            ).all()
        ]
    for workspace_id in workspace_ids:
        rebuild_workspace_notion_index(workspace_id)


def parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
