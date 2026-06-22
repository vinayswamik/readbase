from __future__ import annotations

from src.backend.infrastructure.models import TeamsUserConnection

from .http import is_teams_configured


def public_connection(connection: TeamsUserConnection, teams: list[dict] | None = None) -> dict:
    return {
        "connected": True,
        "configured": is_teams_configured(),
        "microsoft_user_id": connection.microsoft_user_id,
        "tenant_id": connection.tenant_id,
        "display_name": connection.display_name,
        "user_principal_name": connection.user_principal_name,
        "mail": connection.mail,
        "scopes": scopes_list(connection.scopes or ""),
        "teams": teams or [],
    }


def public_team(payload: dict) -> dict:
    return {
        "team_id": str(payload.get("id") or ""),
        "display_name": str(payload.get("displayName") or ""),
        "description": optional_str(payload.get("description")),
        "web_url": optional_str(payload.get("webUrl")),
    }


def scopes_list(value: str) -> list[str]:
    return [scope for scope in value.replace(",", " ").split() if scope]


def optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
