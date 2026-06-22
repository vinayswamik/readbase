from __future__ import annotations

import json
from typing import Any

from src.backend.infrastructure.models import OrgSource, SlackUserConnection, WorkspaceSlackTeam

from .http import is_slack_configured
from .utils import list_scopes


def public_connection(teams: list[dict]) -> dict:
    return {
        "connected": bool(teams),
        "configured": is_slack_configured(),
        "teams": teams,
    }


def public_team(connection: SlackUserConnection) -> dict:
    return {
        "team_id": connection.team_id,
        "team_name": connection.team_name,
        "team_domain": connection.team_domain,
        "slack_user_id": connection.slack_user_id,
        "scopes": list_scopes(connection.scopes or ""),
    }


def public_team_link(team: WorkspaceSlackTeam, user_oauth_connected: bool = False) -> dict:
    return {
        "team_id": team.team_id,
        "team_name": team.team_name,
        "team_domain": team.team_domain,
        "linked_by_user_id": team.linked_by_user_id,
        "linked_at": team.linked_at.isoformat(),
        "updated_at": team.updated_at.isoformat(),
        "user_oauth_connected": user_oauth_connected,
    }


def public_channel(channel: dict, team: dict) -> dict:
    return {
        "team_id": team["team_id"],
        "team_name": team["team_name"],
        "team_domain": team.get("team_domain"),
        "channel_id": str(channel.get("id") or ""),
        "channel_name": str(channel.get("name") or channel.get("name_normalized") or ""),
        "is_private": bool(channel.get("is_private")),
        "is_archived": bool(channel.get("is_archived")),
    }


def _slack_metadata(source: OrgSource) -> dict:
    raw = source.metadata_json or ""
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def public_source(
    source: OrgSource,
    *,
    workspace_id: str,
    user_access: str = "unknown",
    sync_owner_user_id: str | None = None,
) -> dict:
    metadata = _slack_metadata(source)
    return {
        "source_id": source.source_id,
        "workspace_id": workspace_id,
        "team_id": str(metadata.get("team_id") or ""),
        "team_name": str(metadata.get("team_name") or source.display_name or ""),
        "team_domain": metadata.get("team_domain"),
        "channel_id": str(metadata.get("channel_id") or ""),
        "channel_name": str(metadata.get("channel_name") or ""),
        "channel_is_private": bool(metadata.get("channel_is_private")),
        "added_by_user_id": source.added_by_user_id,
        "sync_owner_user_id": sync_owner_user_id or source.sync_owner_user_id or source.added_by_user_id,
        "sync_status": source.sync_status,
        "sync_error": source.sync_error,
        "last_synced_at": source.last_synced_at.isoformat() if source.last_synced_at else None,
        "last_message_ts": str(metadata.get("last_message_ts") or ""),
        "next_sync_at": source.next_sync_at.isoformat() if source.next_sync_at else None,
        "created_at": source.created_at.isoformat(),
        "updated_at": source.updated_at.isoformat(),
        "user_access": user_access,
    }
