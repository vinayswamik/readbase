from __future__ import annotations

import json
import threading
import time
from datetime import timedelta

from sqlalchemy import delete, or_, select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    OrgSource,
    SlackIndexedItem,
    SlackUserConnection,
    WorkspaceMember,
    WorkspaceSlackSource,
    WorkspaceSourceSubscription,
    utc_now,
)
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
    if workspace_id is not None:
        require_workspace_subscription(public_source_id, workspace_id)
    mark_source_syncing(public_source_id)
    try:
        owner_user_id = select_sync_owner(public_source_id)
        source = get_source(public_source_id)
        token = get_valid_slack_access_token(owner_user_id, source["team_id"])
        messages = fetch_channel_messages(source, token)
        items = normalize_messages(source, messages)
        upsert_indexed_items(items)
        rebuild_subscribed_workspace_indexes(public_source_id)
        update_source_success(public_source_id, owner_user_id, messages)
    except Exception as exc:
        return update_source_failure(public_source_id, exc)
    return get_source(public_source_id)


def sync_due_slack_sources(limit: int = 5) -> list[dict]:
    now = utc_now()
    with session_scope() as session:
        sources = session.scalars(
            select(OrgSource)
            .where(
                OrgSource.provider == "slack",
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


def require_workspace_subscription(source_id: str, workspace_id: str) -> None:
    normalized_workspace_id = workspace_id.strip()
    with session_scope() as session:
        subscription = session.scalar(
            select(WorkspaceSourceSubscription).where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                WorkspaceSourceSubscription.source_id == source_id.strip(),
            )
        )
        if subscription is None:
            raise ResourceNotFoundError("Slack source not found.")


def mark_source_syncing(source_id: str) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "slack":
            raise ResourceNotFoundError("Slack source not found.")
        source.sync_status = "syncing"
        source.sync_error = None
        source.updated_at = utc_now()


def select_sync_owner(source_id: str) -> str:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "slack":
            raise ResourceNotFoundError("Slack source not found.")
        metadata = _parse_metadata(source.metadata_json)
        team_id = str(metadata.get("team_id") or "")
        if not team_id:
            raise ResourceNotFoundError("Slack source metadata is missing team_id.")
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
                    SlackUserConnection.team_id == team_id,
                )
            )
            if connection is None:
                continue
            try:
                verify_slack_channel_access(
                    get_valid_slack_access_token(candidate, team_id),
                    str(metadata.get("channel_id") or ""),
                )
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


def rebuild_subscribed_workspace_indexes(source_id: str) -> None:
    with session_scope() as session:
        workspace_ids = [
            row.workspace_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription).where(WorkspaceSourceSubscription.source_id == source_id)
            ).all()
        ]
    for workspace_id in workspace_ids:
        rebuild_workspace_slack_index(workspace_id)


def rebuild_workspace_slack_index(workspace_id: str) -> None:
    normalized_workspace_id = workspace_id.strip()
    with session_scope() as session:
        source_ids = [
            row.source_id
            for row in session.scalars(
                select(WorkspaceSourceSubscription.source_id).join(
                    OrgSource, OrgSource.source_id == WorkspaceSourceSubscription.source_id
                ).where(
                    WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                    OrgSource.provider == "slack",
                )
            ).all()
        ]
        if not source_ids:
            build_slack_index([], normalized_workspace_id)
            return
        rows = session.scalars(select(SlackIndexedItem).where(SlackIndexedItem.source_id.in_(source_ids))).all()
        unique_rows: dict[tuple[str, str, str, str], SlackIndexedItem] = {}
        for row in rows:
            dedupe_key = (row.team_id, row.channel_id, row.item_type, row.item_id)
            existing = unique_rows.get(dedupe_key)
            if existing is None or row.indexed_at > existing.indexed_at:
                unique_rows[dedupe_key] = row
        chunks = [
            {
                "id": slack_chunk_id(normalized_workspace_id, row.team_id, row.channel_id, row.item_type, row.item_id),
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
            for row in unique_rows.values()
        ]
    build_slack_index(chunks, normalized_workspace_id)


def update_source_success(source_id: str, owner_user_id: str, messages: list[dict]) -> None:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "slack":
            raise ResourceNotFoundError("Slack source not found.")
        metadata = _parse_metadata(source.metadata_json)
        max_ts = max([str(message.get("ts") or "") for message in messages] + [str(metadata.get("last_message_ts") or "")])
        metadata["last_message_ts"] = max_ts or str(metadata.get("last_message_ts") or "")
        source.metadata_json = json.dumps(metadata, sort_keys=True)
        source.sync_owner_user_id = owner_user_id
        source.sync_status = "synced"
        source.sync_error = None
        source.last_synced_at = utc_now()
        source.next_sync_at = utc_now() + timedelta(seconds=SLACK_SYNC_INTERVAL_SECONDS)
        source.updated_at = utc_now()
        legacy_source = session.get(WorkspaceSlackSource, source_id)
        if legacy_source is not None:
            legacy_source.sync_owner_user_id = owner_user_id
            legacy_source.sync_status = "synced"
            legacy_source.sync_error = None
            legacy_source.last_synced_at = source.last_synced_at
            legacy_source.last_message_ts = metadata["last_message_ts"]
            legacy_source.next_sync_at = source.next_sync_at
            legacy_source.updated_at = source.updated_at


def update_source_failure(source_id: str, exc: Exception) -> dict:
    retry_seconds = exc.retry_after_seconds if isinstance(exc, SlackRateLimitError) else SLACK_SYNC_INTERVAL_SECONDS
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "slack":
            raise ResourceNotFoundError("Slack source not found.")
        source.sync_status = "needs_reauth" if isinstance(exc, PermissionDeniedError) else "error"
        source.sync_error = str(exc)[:1000]
        source.next_sync_at = utc_now() + timedelta(seconds=retry_seconds)
        source.updated_at = utc_now()
        workspace_id = session.scalar(
            select(WorkspaceSourceSubscription.workspace_id)
            .where(WorkspaceSourceSubscription.source_id == source_id)
            .limit(1)
        )
        legacy_source = session.get(WorkspaceSlackSource, source_id)
        if legacy_source is not None:
            legacy_source.sync_status = source.sync_status
            legacy_source.sync_error = source.sync_error
            legacy_source.next_sync_at = source.next_sync_at
            legacy_source.updated_at = source.updated_at
        return public_source(source, workspace_id=workspace_id or "", user_access="unknown")


def get_source(source_id: str) -> dict:
    with session_scope() as session:
        source = session.get(OrgSource, source_id)
        if source is None or source.provider != "slack":
            raise ResourceNotFoundError("Slack source not found.")
        workspace_id = session.scalar(
            select(WorkspaceSourceSubscription.workspace_id)
            .where(WorkspaceSourceSubscription.source_id == source_id)
            .limit(1)
        )
        payload = public_source(source, workspace_id=workspace_id or "", user_access="unknown")
        payload["org_id"] = source.org_id
        return payload


def purge_org_slack_source(source_id: str) -> None:
    normalized_source_id = source_id.strip()
    with session_scope() as session:
        session.execute(delete(SlackIndexedItem).where(SlackIndexedItem.source_id == normalized_source_id))
        source = session.get(OrgSource, normalized_source_id)
        if source is not None and source.provider == "slack":
            session.delete(source)
        legacy = session.get(WorkspaceSlackSource, normalized_source_id)
        if legacy is not None:
            session.delete(legacy)


def slack_chunk_id(workspace_id: str, team_id: str, channel_id: str, item_type: str, item_id: str) -> str:
    return f"slack:{workspace_id}:{team_id}:{channel_id}:{item_type}:{item_id}"


def _parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
