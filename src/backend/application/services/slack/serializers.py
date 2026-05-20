from __future__ import annotations

from src.backend.infrastructure.models import SlackUserConnection, WorkspaceSlackSource

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


def public_source(source: WorkspaceSlackSource, user_access: str = "unknown") -> dict:
    return {
        "source_id": source.source_id,
        "workspace_id": source.workspace_id,
        "team_id": source.team_id,
        "team_name": source.team_name,
        "team_domain": source.team_domain,
        "channel_id": source.channel_id,
        "channel_name": source.channel_name,
        "channel_is_private": source.channel_is_private,
        "added_by_user_id": source.added_by_user_id,
        "sync_owner_user_id": source.sync_owner_user_id,
        "sync_status": source.sync_status,
        "sync_error": source.sync_error,
        "last_synced_at": source.last_synced_at.isoformat() if source.last_synced_at else None,
        "last_message_ts": source.last_message_ts,
        "next_sync_at": source.next_sync_at.isoformat() if source.next_sync_at else None,
        "created_at": source.created_at.isoformat(),
        "updated_at": source.updated_at.isoformat(),
        "user_access": user_access,
    }
