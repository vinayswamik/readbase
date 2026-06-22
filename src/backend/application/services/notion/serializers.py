from __future__ import annotations

import json

from src.backend.infrastructure.models import NotionUserConnection, OrgSource


def public_connection(connection: NotionUserConnection) -> dict:
    return {
        "connected": True,
        "configured": True,
        "workspace_id": connection.notion_workspace_id,
        "workspace_name": connection.workspace_name,
        "workspace_icon": connection.workspace_icon,
        "bot_id": connection.bot_id,
        "owner_type": connection.owner_type,
        "owner_name": connection.owner_name,
    }


def _metadata(source: OrgSource) -> dict:
    raw = source.metadata_json or ""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def public_source(
    source: OrgSource,
    *,
    workspace_id: str,
    user_access: str = "unknown",
    sync_owner_user_id: str | None = None,
) -> dict:
    metadata = _metadata(source)
    return {
        "source_id": source.source_id,
        "workspace_id": workspace_id,
        "notion_workspace_id": str(metadata.get("notion_workspace_id") or ""),
        "database_id": str(metadata.get("database_id") or ""),
        "database_title": str(metadata.get("database_title") or ""),
        "added_by_user_id": source.added_by_user_id,
        "sync_owner_user_id": sync_owner_user_id or source.sync_owner_user_id or source.added_by_user_id,
        "sync_status": source.sync_status,
        "sync_error": source.sync_error,
        "last_synced_at": iso(source.last_synced_at),
        "next_sync_at": iso(source.next_sync_at),
        "created_at": iso(source.created_at),
        "updated_at": iso(source.updated_at),
        "user_access": user_access,
    }


def iso(value) -> str | None:
    return value.isoformat() if value else None
