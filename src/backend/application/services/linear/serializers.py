from __future__ import annotations

from src.backend.infrastructure.models import LinearUserConnection, WorkspaceLinearSource


def public_connection(connection: LinearUserConnection) -> dict:
    return {
        "connected": True,
        "configured": True,
        "linear_user_id": connection.linear_user_id,
        "workspace_id": connection.workspace_id,
        "workspace_name": connection.workspace_name,
        "name": connection.name,
        "email": connection.email,
        "scopes": [scope for scope in (connection.scopes or "").replace(",", " ").split() if scope],
    }


def public_source(source: WorkspaceLinearSource, user_access: str = "unknown") -> dict:
    return {
        "source_id": source.source_id,
        "workspace_id": source.workspace_id,
        "linear_team_id": source.linear_team_id,
        "team_name": source.team_name,
        "linear_project_id": source.linear_project_id,
        "project_name": source.project_name,
        "added_by_user_id": source.added_by_user_id,
        "sync_owner_user_id": source.sync_owner_user_id,
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
