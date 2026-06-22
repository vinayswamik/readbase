from __future__ import annotations

import threading
import time
from datetime import timedelta

from sqlalchemy import delete, or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    JiraIndexedItem,
    JiraUserSite,
    OrgSource,
    WorkspaceJiraSource,
    WorkspaceMember,
    WorkspaceSourceSubscription,
    utc_now,
)
from src.backend.infrastructure.retrieval.retriever import build_jira_index

from .auth import get_valid_jira_access_token
from .constants import JIRA_SYNC_INTERVAL_SECONDS, JIRA_SYNC_LIMIT, JIRA_SYNC_SCHEDULER_DISABLED
from .http import jira_request
from .normalize import normalize_issues
from .serializers import public_source

_scheduler_started = False


def sync_workspace_jira_source(source_id: str, workspace_id: str | None = None) -> dict:
    public_source_id = source_id.strip()
    if workspace_id is not None:
        require_workspace_subscription(public_source_id, workspace_id)
    mark_source_syncing(public_source_id)

    try:
        owner_user_id = select_sync_owner(public_source_id)
        access_token = get_valid_jira_access_token(owner_user_id)
        source = get_source(public_source_id)
        issues = fetch_project_issues(source, access_token)
        items = normalize_issues(source, issues)
        replace_indexed_items(source, items)
        rebuild_subscribed_workspace_indexes(public_source_id)
        update_source_success(public_source_id, owner_user_id)
        return get_source(public_source_id)
    except Exception as exc:
        return update_source_failure(public_source_id, exc)


def sync_due_jira_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(OrgSource)
            .where(
                OrgSource.provider == "jira",
                OrgSource.sync_status != "syncing",
                or_(
                    OrgSource.next_sync_at.is_(None),
                    OrgSource.next_sync_at <= now,
                ),
            )
            .order_by(OrgSource.next_sync_at.asc())
            .limit(limit)
        ).all()
        source_ids = [source.source_id for source in sources]
    return [sync_workspace_jira_source(source_id) for source_id in source_ids]


def start_jira_sync_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started or JIRA_SYNC_SCHEDULER_DISABLED:
        return
    _scheduler_started = True

    def run() -> None:
        while True:
            try:
                sync_due_jira_sources()
            except Exception:
                pass
            time.sleep(max(60, JIRA_SYNC_INTERVAL_SECONDS))

    thread = threading.Thread(target=run, name="readbase-jira-sync", daemon=True)
    thread.start()


def select_sync_owner(source_id: str) -> str:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "jira":
            raise ResourceNotFoundError("Jira source not found.")
        metadata = parse_metadata(source)
        candidates = [source.sync_owner_user_id, source.added_by_user_id]
        workspace_ids = [
            row.workspace_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription).where(WorkspaceSourceSubscription.source_id == source_id)
            ).all()
        ]
        for workspace_id in workspace_ids:
            members = session.scalars(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    or_(
                        WorkspaceMember.connector_manager.is_(True),
                        WorkspaceMember.user_id == source.added_by_user_id,
                    ),
                )
            ).all()
            candidates.extend(member.user_id for member in members if member.user_id)
        for candidate in dict.fromkeys(candidates):
            if not candidate:
                continue
            has_site = session.scalar(
                select(JiraUserSite).where(
                    JiraUserSite.user_id == candidate,
                    JiraUserSite.cloud_id == str(metadata.get("cloud_id") or ""),
                )
            )
            if has_site is not None:
                return candidate
    raise PermissionDeniedError("No connected Jira user can sync this project.")


def fetch_project_issues(source: dict, access_token: str) -> list[dict]:
    body = {
        "jql": f'project = "{source["project_key"]}" ORDER BY updated DESC',
        "maxResults": JIRA_SYNC_LIMIT,
        "fields": ["summary", "description", "status", "assignee", "reporter", "labels", "priority", "updated", "comment", "worklog", "attachment"],
    }
    try:
        data = jira_request(source["cloud_id"], "/rest/api/3/search/jql", access_token, method="POST", body=body)
    except ResourceNotFoundError:
        data = jira_request(source["cloud_id"], "/rest/api/3/search", access_token, method="POST", body=body)
    return data.get("issues", []) if isinstance(data, dict) else []


def replace_indexed_items(source: dict, items: list[dict]) -> None:
    with session_scope() as session:
        session.execute(delete(JiraIndexedItem).where(JiraIndexedItem.source_id == source["source_id"]))
        for item in items:
            session.add(JiraIndexedItem(**item))


def rebuild_workspace_jira_index(workspace_id: str) -> None:
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        source_ids = [
            row.source_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription.source_id)
                .join(OrgSource, OrgSource.source_id == WorkspaceSourceSubscription.source_id)
                .where(
                    WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                    OrgSource.provider == "jira",
                )
            ).all()
        ]
        if not source_ids:
            build_jira_index([], normalized_workspace_id)
            return
        rows = session.scalars(select(JiraIndexedItem).where(JiraIndexedItem.source_id.in_(source_ids))).all()
        unique_rows: dict[tuple[str, str, str], JiraIndexedItem] = {}
        for row in rows:
            key = (row.issue_id, row.item_type, row.item_id)
            existing = unique_rows.get(key)
            if existing is None or row.indexed_at > existing.indexed_at:
                unique_rows[key] = row
        chunks = [
            {
                "id": f"jira:{normalized_workspace_id}:{row.project_key}:{row.item_type}:{row.item_id}",
                "path": f"jira/{row.project_key}/{row.issue_key}/{row.item_type}/{row.item_id}",
                "text": f"{row.title}\n\n{row.body}",
                "source_url": row.source_url,
                "cloud_id": row.cloud_id,
                "project_id": row.project_id,
                "project_key": row.project_key,
                "issue_id": row.issue_id,
                "issue_key": row.issue_key,
                "item_type": row.item_type,
                "item_id": row.item_id,
            }
            for row in unique_rows.values()
        ]
    build_jira_index(chunks, normalized_workspace_id)


def get_source(source_id: str) -> dict:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "jira":
            raise ResourceNotFoundError("Jira source not found.")
        workspace_id = session.scalar(
            select(WorkspaceSourceSubscription.workspace_id)
            .where(WorkspaceSourceSubscription.source_id == source_id)
            .limit(1)
        )
        sync_owner_user_id = session.scalar(
            select(WorkspaceJiraSource.sync_owner_user_id)
            .where(WorkspaceJiraSource.source_id == source_id)
            .limit(1)
        )
        payload = public_source(
            source,
            workspace_id=workspace_id or "",
            sync_owner_user_id=sync_owner_user_id,
            user_access="unknown",
        )
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
            raise ResourceNotFoundError("Jira source not found.")


def mark_source_syncing(source_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "jira":
            raise ResourceNotFoundError("Jira source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()


def rebuild_subscribed_workspace_indexes(source_id: str) -> None:
    with session_scope() as session:
        workspace_ids = [
            row.workspace_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription).where(WorkspaceSourceSubscription.source_id == source_id)
            ).all()
        ]
    for workspace_id in workspace_ids:
        rebuild_workspace_jira_index(workspace_id)


def update_source_success(source_id: str, owner_user_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "jira":
            raise ResourceNotFoundError("Jira source not found.")
        source.sync_owner_user_id = owner_user_id
        source.sync_status = "synced"
        source.sync_error = None
        source.last_synced_at = utc_now()
        source.next_sync_at = utc_now() + timedelta(seconds=JIRA_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy = session.get(WorkspaceJiraSource, source_id)
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
        if source is None or source.provider != "jira":
            raise ResourceNotFoundError("Jira source not found.")
        source.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
        source.sync_error = str(exc)[:1000]
        source.next_sync_at = utc_now() + timedelta(seconds=JIRA_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy = session.get(WorkspaceJiraSource, source_id)
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


def parse_metadata(source: OrgSource) -> dict:
    raw = source.metadata_json or ""
    if not raw:
        return {}
    import json

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
