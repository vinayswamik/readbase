from __future__ import annotations

from src.backend.infrastructure.models import JiraUserConnection, JiraUserSite, WorkspaceJiraSource

from .utils import format_datetime, list_str, optional_str, split_scopes


def public_connection(connection: JiraUserConnection, sites: list[dict]) -> dict:
    return {
        "connected": True,
        "account_id": connection.atlassian_account_id,
        "account_email": connection.account_email,
        "account_name": connection.account_name,
        "scopes": split_scopes(connection.scopes),
        "sites": sites,
    }


def public_site(site: JiraUserSite) -> dict:
    return {
        "cloud_id": site.cloud_id,
        "name": site.site_name,
        "url": site.site_url,
        "scopes": split_scopes(site.scopes),
        "avatar_url": site.avatar_url,
    }


def public_sites_for_resources(resources: list[dict]) -> list[dict]:
    sites = []
    for resource in resources:
        cloud_id = optional_str(resource.get("id"))
        name = optional_str(resource.get("name"))
        url = optional_str(resource.get("url"))
        if cloud_id and name and url:
            sites.append(
                {
                    "cloud_id": cloud_id,
                    "name": name,
                    "url": url,
                    "scopes": list_str(resource.get("scopes")),
                    "avatar_url": optional_str(resource.get("avatarUrl")),
                }
            )
    return sites


def public_source(source: WorkspaceJiraSource, user_access: str) -> dict:
    return {
        "source_id": source.source_id,
        "workspace_id": source.workspace_id,
        "cloud_id": source.cloud_id,
        "site_name": source.site_name,
        "site_url": source.site_url,
        "project_id": source.project_id,
        "project_key": source.project_key,
        "project_name": source.project_name,
        "added_by_user_id": source.added_by_user_id,
        "sync_owner_user_id": source.sync_owner_user_id,
        "sync_status": source.sync_status,
        "sync_error": source.sync_error,
        "last_synced_at": format_datetime(source.last_synced_at),
        "next_sync_at": format_datetime(source.next_sync_at),
        "created_at": format_datetime(source.created_at),
        "updated_at": format_datetime(source.updated_at),
        "user_access": user_access,
    }
