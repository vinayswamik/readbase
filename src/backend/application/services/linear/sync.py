from __future__ import annotations

import json
import threading
import time
from datetime import timedelta

from sqlalchemy import or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    LinearIndexedItem,
    LinearUserConnection,
    OrgSource,
    WorkspaceLinearSource,
    WorkspaceMember,
    WorkspaceSourceSubscription,
    utc_now,
)
from src.backend.infrastructure.retrieval.retriever import build_linear_index

from .auth import get_valid_linear_access_token
from .constants import LINEAR_SYNC_INTERVAL_SECONDS, LINEAR_SYNC_LIMIT, LINEAR_SYNC_SCHEDULER_DISABLED
from .http import linear_graphql_request
from .normalize import normalize_issues
from .serializers import public_source

_scheduler_started = False


def sync_workspace_linear_source(source_id: str, workspace_id: str | None = None) -> dict:
    if workspace_id is not None:
        require_workspace_subscription(source_id, workspace_id)
    mark_source_syncing(source_id)
    try:
        owner_user_id = select_sync_owner(source_id)
        source = get_source(source_id)
        token = get_valid_linear_access_token(owner_user_id)
        issues = fetch_issues(source, token)
        items = normalize_issues(source, issues)
        upsert_indexed_items(items)
        rebuild_subscribed_workspace_indexes(source_id)
        update_source_success(source_id, owner_user_id)
    except Exception as exc:
        return update_source_failure(source_id, exc)
    return get_source(source_id)


def sync_due_linear_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(OrgSource)
            .where(
                OrgSource.provider == "linear",
                OrgSource.sync_status != "syncing",
                or_(OrgSource.next_sync_at.is_(None), OrgSource.next_sync_at <= now),
            )
            .order_by(OrgSource.next_sync_at.asc())
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


def fetch_issues(source: dict, token: str) -> list[dict]:
    filters = {"team": {"id": {"eq": source["linear_team_id"]}}}
    if source.get("linear_project_id"):
        filters["project"] = {"id": {"eq": source["linear_project_id"]}}
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
        normalized_workspace_id = workspace_id.strip()
        source_ids = [
            row.source_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription.source_id)
                .join(OrgSource, OrgSource.source_id == WorkspaceSourceSubscription.source_id)
                .where(
                    WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                    OrgSource.provider == "linear",
                )
            ).all()
        ]
        if not source_ids:
            build_linear_index([], normalized_workspace_id)
            return
        rows = session.scalars(select(LinearIndexedItem).where(LinearIndexedItem.source_id.in_(source_ids))).all()
        unique_rows: dict[tuple[str, str], LinearIndexedItem] = {}
        for row in rows:
            key = (row.item_type, row.item_id)
            existing = unique_rows.get(key)
            if existing is None or row.indexed_at > existing.indexed_at:
                unique_rows[key] = row
        chunks = [
            {
                "id": f"linear:{normalized_workspace_id}:{row.item_type}:{row.item_id}",
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
            for row in unique_rows.values()
        ]
    build_linear_index(chunks, normalized_workspace_id)


def select_sync_owner(source_id: str) -> str:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "linear":
            raise ResourceNotFoundError("Linear source not found.")
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
            if candidate and session.scalar(select(LinearUserConnection).where(LinearUserConnection.user_id == candidate)):
                return candidate
    raise PermissionDeniedError("No connected Linear user can sync this source.")


def mark_source_syncing(source_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id.strip())
        if source is None or source.provider != "linear":
            raise ResourceNotFoundError("Linear source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()


def update_source_success(source_id: str, owner_user_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "linear":
            raise ResourceNotFoundError("Linear source not found.")
        source.sync_owner_user_id = owner_user_id
        source.sync_status = "synced"
        source.sync_error = None
        source.last_synced_at = utc_now()
        source.next_sync_at = utc_now() + timedelta(seconds=LINEAR_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy = session.get(WorkspaceLinearSource, source_id)
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
        if source is None or source.provider != "linear":
            raise ResourceNotFoundError("Linear source not found.")
        source.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
        source.sync_error = str(exc)[:1000]
        source.next_sync_at = utc_now() + timedelta(seconds=LINEAR_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy = session.get(WorkspaceLinearSource, source_id)
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
        if source is None or source.provider != "linear":
            raise ResourceNotFoundError("Linear source not found.")
        metadata = parse_metadata(source.metadata_json)
        workspace_id = session.scalar(
            select(WorkspaceSourceSubscription.workspace_id)
            .where(WorkspaceSourceSubscription.source_id == source.source_id)
            .limit(1)
        )
        sync_owner_user_id = session.scalar(
            select(WorkspaceLinearSource.sync_owner_user_id)
            .where(WorkspaceLinearSource.source_id == source.source_id)
            .limit(1)
        )
        payload = public_source(
            source,
            workspace_id=workspace_id or "",
            sync_owner_user_id=sync_owner_user_id,
            user_access="unknown",
        )
        payload["linear_team_id"] = str(metadata.get("linear_team_id") or "")
        payload["team_name"] = str(metadata.get("team_name") or "")
        payload["linear_project_id"] = metadata.get("linear_project_id")
        payload["project_name"] = metadata.get("project_name")
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
            raise ResourceNotFoundError("Linear source not found.")


def rebuild_subscribed_workspace_indexes(source_id: str) -> None:
    with session_scope() as session:
        workspace_ids = [
            row.workspace_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription).where(WorkspaceSourceSubscription.source_id == source_id)
            ).all()
        ]
    for workspace_id in workspace_ids:
        rebuild_workspace_linear_index(workspace_id)


def parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
