from __future__ import annotations

import threading
import time
from datetime import timedelta

from sqlalchemy import delete, or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import JiraIndexedItem, JiraUserSite, WorkspaceJiraSource, WorkspaceMember, utc_now
from src.backend.infrastructure.retrieval.retriever import build_jira_index

from .auth import get_valid_jira_access_token
from .constants import JIRA_SYNC_INTERVAL_SECONDS, JIRA_SYNC_LIMIT, JIRA_SYNC_SCHEDULER_DISABLED
from .http import jira_request
from .normalize import normalize_issues
from .serializers import public_source

_scheduler_started = False


def sync_workspace_jira_source(source_id: str, workspace_id: str | None = None) -> dict:
    with session_scope() as session:
        source = session.get(WorkspaceJiraSource, source_id.strip())
        if source is None:
            raise ResourceNotFoundError("Jira source not found.")
        if workspace_id is not None and source.workspace_id != workspace_id.strip():
            raise ResourceNotFoundError("Jira source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()
        public_source_id = source.source_id

    try:
        owner_user_id = select_sync_owner(public_source_id)
        access_token = get_valid_jira_access_token(owner_user_id)
        source = get_source(public_source_id)
        issues = fetch_project_issues(source, access_token)
        items = normalize_issues(source, issues)
        replace_indexed_items(source, items)
        rebuild_workspace_jira_index(source["workspace_id"])
        with session_scope() as session:
            saved = session.get(WorkspaceJiraSource, public_source_id)
            if saved is None:
                raise ResourceNotFoundError("Jira source not found.")
            saved.sync_owner_user_id = owner_user_id
            saved.sync_status = "synced"
            saved.sync_error = None
            saved.last_synced_at = utc_now()
            saved.next_sync_at = utc_now() + timedelta(seconds=JIRA_SYNC_INTERVAL_SECONDS)
            saved.updated_at = utc_now()
            return public_source(saved, user_access="unknown")
    except Exception as exc:
        with session_scope() as session:
            failed = session.get(WorkspaceJiraSource, public_source_id)
            if failed is not None:
                failed.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
                failed.sync_error = str(exc)[:1000]
                failed.next_sync_at = utc_now() + timedelta(seconds=JIRA_SYNC_INTERVAL_SECONDS)
                failed.updated_at = utc_now()
                return public_source(failed, user_access="unknown")
        raise


def sync_due_jira_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(WorkspaceJiraSource)
            .where(
                WorkspaceJiraSource.sync_status != "syncing",
                or_(
                    WorkspaceJiraSource.next_sync_at.is_(None),
                    WorkspaceJiraSource.next_sync_at <= now,
                ),
            )
            .order_by(WorkspaceJiraSource.next_sync_at.asc())
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
        source = session.get(WorkspaceJiraSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Jira source not found.")
        candidates = [source.sync_owner_user_id]
        members = session.scalars(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == source.workspace_id,
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
                    JiraUserSite.cloud_id == source.cloud_id,
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
        rows = session.scalars(select(JiraIndexedItem).where(JiraIndexedItem.workspace_id == workspace_id)).all()
        chunks = [
            {
                "id": f"jira:{row.source_id}:{row.item_type}:{row.item_id}",
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
            for row in rows
        ]
    build_jira_index(chunks, workspace_id)


def get_source(source_id: str) -> dict:
    with session_scope() as session:
        source = session.get(WorkspaceJiraSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Jira source not found.")
        return public_source(source, user_access="unknown")
