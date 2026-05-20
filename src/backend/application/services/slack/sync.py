from __future__ import annotations

import threading
import time
from datetime import timedelta

from sqlalchemy import or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import SlackIndexedItem, SlackUserConnection, WorkspaceMember, WorkspaceSlackSource, utc_now
from src.backend.infrastructure.retrieval.retriever import build_slack_index

from .auth import get_valid_slack_access_token
from .constants import SLACK_SYNC_INTERVAL_SECONDS, SLACK_SYNC_LIMIT, SLACK_SYNC_SCHEDULER_DISABLED, SLACK_THREAD_SYNC_LIMIT
from .http import SlackRateLimitError, slack_api_request
from .normalize import normalize_messages
from .permissions import verify_slack_channel_access
from .serializers import public_source

_scheduler_started = False


def sync_workspace_slack_source(source_id: str, workspace_id: str | None = None) -> dict:
    public_source_id = source_id.strip()
    mark_source_syncing(public_source_id, workspace_id)
    try:
        owner_user_id = select_sync_owner(public_source_id)
        token = get_valid_slack_access_token(owner_user_id, get_source(public_source_id)["team_id"])
        source = get_source(public_source_id)
        messages = fetch_channel_messages(source, token)
        items = normalize_messages(source, messages)
        upsert_indexed_items(items)
        rebuild_workspace_slack_index(source["workspace_id"])
        update_source_success(public_source_id, owner_user_id, messages)
    except Exception as exc:
        return update_source_failure(public_source_id, exc)
    return get_source(public_source_id)


def sync_due_slack_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(WorkspaceSlackSource)
            .where(
                WorkspaceSlackSource.sync_status != "syncing",
                or_(
                    WorkspaceSlackSource.next_sync_at.is_(None),
                    WorkspaceSlackSource.next_sync_at <= now,
                ),
            )
            .order_by(WorkspaceSlackSource.next_sync_at.asc())
            .limit(limit)
        ).all()
        source_ids = [source.source_id for source in sources]
    return [sync_workspace_slack_source(source_id) for source_id in source_ids]


def start_slack_sync_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started or SLACK_SYNC_SCHEDULER_DISABLED:
        return
    _scheduler_started = True

    def run() -> None:
        while True:
            try:
                sync_due_slack_sources()
            except Exception:
                pass
            time.sleep(max(60, SLACK_SYNC_INTERVAL_SECONDS))

    thread = threading.Thread(target=run, name="readbase-slack-sync", daemon=True)
    thread.start()


def mark_source_syncing(source_id: str, workspace_id: str | None) -> None:
    with session_scope() as session:
        source = session.get(WorkspaceSlackSource, source_id)
        if source is None or (workspace_id is not None and source.workspace_id != workspace_id.strip()):
            raise ResourceNotFoundError("Slack source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()


def select_sync_owner(source_id: str) -> str:
    with session_scope() as session:
        source = session.get(WorkspaceSlackSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Slack source not found.")
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
            connection = session.scalar(
                select(SlackUserConnection).where(
                    SlackUserConnection.user_id == candidate,
                    SlackUserConnection.team_id == source.team_id,
                )
            )
            if connection is None:
                continue
            try:
                verify_slack_channel_access(get_valid_slack_access_token(candidate, source.team_id), source.channel_id)
                return candidate
            except Exception:
                continue
    raise PermissionDeniedError("No connected Slack user can sync this channel.")


def fetch_channel_messages(source: dict, token: str) -> list[dict]:
    query = {
        "channel": source["channel_id"],
        "limit": str(SLACK_SYNC_LIMIT),
    }
    if source.get("last_message_ts"):
        query["oldest"] = source["last_message_ts"]
        query["inclusive"] = "false"
    payload = slack_api_request("/conversations.history", token=token, query=query)
    messages = list(payload.get("messages", []) if isinstance(payload, dict) else [])
    messages.extend(fetch_thread_replies(source, token, messages))
    return messages


def fetch_thread_replies(source: dict, token: str, messages: list[dict]) -> list[dict]:
    replies: list[dict] = []
    for message in messages[:SLACK_THREAD_SYNC_LIMIT]:
        if int(message.get("reply_count") or 0) <= 0:
            continue
        thread_ts = str(message.get("thread_ts") or message.get("ts") or "")
        if not thread_ts:
            continue
        payload = slack_api_request(
            "/conversations.replies",
            token=token,
            query={"channel": source["channel_id"], "ts": thread_ts, "limit": str(SLACK_SYNC_LIMIT)},
        )
        thread_messages = payload.get("messages", []) if isinstance(payload, dict) else []
        replies.extend(thread_messages[1:])
    return replies


def upsert_indexed_items(items: list[dict]) -> None:
    with session_scope() as session:
        for item in items:
            existing = session.scalar(
                select(SlackIndexedItem).where(
                    SlackIndexedItem.source_id == item["source_id"],
                    SlackIndexedItem.item_type == item["item_type"],
                    SlackIndexedItem.item_id == item["item_id"],
                )
            )
            if existing is None:
                session.add(SlackIndexedItem(**item))
                continue
            for key, value in item.items():
                setattr(existing, key, value)


def rebuild_workspace_slack_index(workspace_id: str) -> None:
    with session_scope() as session:
        rows = session.scalars(select(SlackIndexedItem).where(SlackIndexedItem.workspace_id == workspace_id)).all()
        chunks = [
            {
                "id": f"slack:{row.source_id}:{row.item_type}:{row.item_id}",
                "path": f"slack/{row.team_name}/{row.channel_name}/{row.message_ts}",
                "text": f"{row.title}\n\n{row.body}",
                "source_url": row.source_url,
                "team_id": row.team_id,
                "team_name": row.team_name,
                "channel_id": row.channel_id,
                "channel_name": row.channel_name,
                "message_ts": row.message_ts,
                "thread_ts": row.thread_ts or "",
                "item_type": row.item_type,
                "item_id": row.item_id,
            }
            for row in rows
        ]
    build_slack_index(chunks, workspace_id)


def update_source_success(source_id: str, owner_user_id: str, messages: list[dict]) -> None:
    with session_scope() as session:
        source = session.get(WorkspaceSlackSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Slack source not found.")
        max_ts = max([str(message.get("ts") or "") for message in messages] + [source.last_message_ts or ""])
        source.sync_owner_user_id = owner_user_id
        source.sync_status = "synced"
        source.sync_error = None
        source.last_synced_at = utc_now()
        source.last_message_ts = max_ts or source.last_message_ts
        source.next_sync_at = utc_now() + timedelta(seconds=SLACK_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()


def update_source_failure(source_id: str, exc: Exception) -> dict:
    retry_seconds = exc.retry_after_seconds if isinstance(exc, SlackRateLimitError) else SLACK_SYNC_INTERVAL_SECONDS
    with session_scope() as session:
        source = session.get(WorkspaceSlackSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Slack source not found.")
        source.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
        source.sync_error = str(exc)[:1000]
        source.next_sync_at = utc_now() + timedelta(seconds=retry_seconds)
        source.updated_at = utc_now()
        return public_source(source, user_access="unknown")


def get_source(source_id: str) -> dict:
    with session_scope() as session:
        source = session.get(WorkspaceSlackSource, source_id)
        if source is None:
            raise ResourceNotFoundError("Slack source not found.")
        return public_source(source, user_access="unknown")
