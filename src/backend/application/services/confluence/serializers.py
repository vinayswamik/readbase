from __future__ import annotations

import json

from src.backend.infrastructure.models import ConfluenceUserConnection, ConfluenceUserSite, OrgSource


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
        "cloud_id": str(metadata.get("cloud_id") or ""),
        "site_name": str(metadata.get("site_name") or ""),
        "site_url": str(metadata.get("site_url") or ""),
        "space_id": str(metadata.get("space_id") or ""),
        "space_key": str(metadata.get("space_key") or ""),
        "space_name": str(metadata.get("space_name") or ""),
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
