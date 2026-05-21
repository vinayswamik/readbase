from __future__ import annotations

from src.backend.infrastructure.models import ConfluenceUserConnection, ConfluenceUserSite, WorkspaceConfluenceSource


def public_connection(connection: ConfluenceUserConnection, sites: list[dict]) -> dict:
    return {
        "connected": True,
        "configured": True,
        "account_id": connection.atlassian_account_id,
        "account_email": connection.account_email,
        "account_name": connection.account_name,
        "scopes": [scope for scope in (connection.scopes or "").replace(",", " ").split() if scope],
        "sites": sites,
    }


def public_site(site: ConfluenceUserSite) -> dict:
    return {"cloud_id": site.cloud_id, "name": site.site_name, "url": site.site_url, "scopes": [scope for scope in (site.scopes or "").split() if scope], "avatar_url": site.avatar_url}


def public_source(source: WorkspaceConfluenceSource, user_access: str = "unknown") -> dict:
    return {
        "source_id": source.source_id,
        "workspace_id": source.workspace_id,
        "cloud_id": source.cloud_id,
        "site_name": source.site_name,
        "site_url": source.site_url,
        "space_id": source.space_id,
        "space_key": source.space_key,
        "space_name": source.space_name,
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
