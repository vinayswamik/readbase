from __future__ import annotations

import threading
import time
from datetime import timedelta

from sqlalchemy import or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import LinearIndexedItem, LinearUserConnection, WorkspaceLinearSource, WorkspaceMember, utc_now
from src.backend.infrastructure.retrieval.retriever import build_linear_index

from .auth import get_valid_linear_access_token
from .constants import LINEAR_SYNC_INTERVAL_SECONDS, LINEAR_SYNC_LIMIT, LINEAR_SYNC_SCHEDULER_DISABLED
from .http import linear_graphql_request
from .normalize import normalize_issues
from .serializers import public_source

_scheduler_started = False


def sync_workspace_linear_source(source_id: str, workspace_id: str | None = None) -> dict:
    mark_source_syncing(source_id, workspace_id)
    try:
        owner_user_id = select_sync_owner(source_id)
        source = get_source_row(source_id)
        token = get_valid_linear_access_token(owner_user_id)
        issues = fetch_issues(source, token)
        items = normalize_issues(source, issues)
        upsert_indexed_items(items)
        rebuild_workspace_linear_index(source.workspace_id)
        update_source_success(source_id, owner_user_id)
    except Exception as exc:
        return update_source_failure(source_id, exc)
    return get_source(source_id)


def sync_due_linear_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(WorkspaceLinearSource)
            .where(WorkspaceLinearSource.sync_status != "syncing", or_(WorkspaceLinearSource.next_sync_at.is_(None), WorkspaceLinearSource.next_sync_at <= now))
            .order_by(WorkspaceLinearSource.next_sync_at.asc())
            .limit(limit)
        ).all()
        source_ids = [source.source_id for source in sources]
    return [sync_workspace_linear_source(source_id) for source_id in source_ids]


def start_linear_sync_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started or LINEAR_SYNC_SCHEDULER_DISABLED:
        return
    _scheduler_started = True

    def run() -> None:
        while True:
            try:
                sync_due_linear_sources()
            except Exception:
                pass
            time.sleep(max(60, LINEAR_SYNC_INTERVAL_SECONDS))

    threading.Thread(target=run, name="readbase-linear-sync", daemon=True).start()


def fetch_issues(source: WorkspaceLinearSource, token: str) -> list[dict]:
    filters = {"team": {"id": {"eq": source.linear_team_id}}}
    if source.linear_project_id:
        filters["project"] = {"id": {"eq": source.linear_project_id}}
    data = linear_graphql_request(
        """
        query($filter: IssueFilter, $first: Int!) {
          issues(filter: $filter, first: $first, orderBy: updatedAt) {
            nodes {
              id identifier title description url updatedAt
              comments(first: 50) { nodes { id body updatedAt } }
            }
          }
        }
        """,
        token,
        {"filter": filters, "first": LINEAR_SYNC_LIMIT},
    )
    issues = data.get("issues") if isinstance(data.get("issues"), dict) else {}
    return [issue for issue in issues.get("nodes", []) if isinstance(issue, dict)]


def upsert_indexed_items(items: list[dict]) -> None:
    with session_scope() as session:
        for item in items:
            existing = session.scalar(
                select(LinearIndexedItem).where(
                    LinearIndexedItem.source_id == item["source_id"],
                    LinearIndexedItem.item_type == item["item_type"],
                    LinearIndexedItem.item_id == item["item_id"],
                )
            )
            if existing is None:
                session.add(LinearIndexedItem(**item))
                continue
            for key, value in item.items():
                setattr(existing, key, value)


def rebuild_workspace_linear_index(workspace_id: str) -> None:
    with session_scope() as session:
        rows = session.scalars(select(LinearIndexedItem).where(LinearIndexedItem.workspace_id == workspace_id)).all()
        chunks = [
            {
                "id": f"linear:{row.source_id}:{row.item_type}:{row.item_id}",
                "path": f"linear/{row.issue_key}/{row.item_type}",
                "text": f"{row.title}\n\n{row.body}",
                "source_url": row.source_url,
                "linear_team_id": row.linear_team_id,
                "linear_project_id": row.linear_project_id or "",
                "issue_id": row.issue_id,
                "issue_key": row.issue_key,
                "item_type": row.item_type,
                "item_id": row.item_id,
            }
            for row in rows
        ]
    build_linear_index(chunks, workspace_id)


def select_sync_owner(source_id: str) -> str:
    with session_scope() as session:
        source = session.get(WorkspaceLinearSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Linear source not found.")
        candidates = [source.sync_owner_user_id]
        members = session.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == source.workspace_id, WorkspaceMember.connector_manager.is_(True))).all()
        candidates.extend(member.user_id for member in members if member.user_id)
        for candidate in dict.fromkeys(candidates):
            if candidate and session.scalar(select(LinearUserConnection).where(LinearUserConnection.user_id == candidate)):
                return candidate
    raise PermissionDeniedError("No connected Linear user can sync this source.")


def mark_source_syncing(source_id: str, workspace_id: str | None) -> None:
    with session_scope() as session:
        source = session.get(WorkspaceLinearSource, source_id.strip())
        if source is None or (workspace_id is not None and source.workspace_id != workspace_id.strip()):
            raise ResourceNotFoundError("Linear source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()


def update_source_success(source_id: str, owner_user_id: str) -> None:
    with session_scope() as session:
        source = session.get(WorkspaceLinearSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Linear source not found.")
        source.sync_owner_user_id = owner_user_id
        source.sync_status = "synced"
        source.sync_error = None
        source.last_synced_at = utc_now()
        source.next_sync_at = utc_now() + timedelta(seconds=LINEAR_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()


def update_source_failure(source_id: str, exc: Exception) -> dict:
    with session_scope() as session:
        source = session.get(WorkspaceLinearSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Linear source not found.")
        source.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
        source.sync_error = str(exc)[:1000]
        source.next_sync_at = utc_now() + timedelta(seconds=LINEAR_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        return public_source(source, user_access="unknown")


def get_source(source_id: str) -> dict:
    return public_source(get_source_row(source_id), user_access="unknown")


def get_source_row(source_id: str) -> WorkspaceLinearSource:
    with session_scope() as session:
        source = session.get(WorkspaceLinearSource, source_id.strip())
        if source is None:
            raise ResourceNotFoundError("Linear source not found.")
        session.expunge(source)
        return source
