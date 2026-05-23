from __future__ import annotations

import os
import urllib.parse
from datetime import timedelta
from secrets import token_urlsafe
from typing import Any

from sqlalchemy import delete, select

from src.backend.application.services.auth_service import APP_BASE_URL
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.application.services.jira.crypto import decrypt_token, encrypt_token
from src.backend.application.services.jira.utils import as_utc
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import ConfluenceIndexedItem, ConfluenceUserConnection, ConfluenceUserSite, ConfluenceVisibilityCache, WorkspaceConfluenceSource, utc_now

from .constants import ATLASSIAN_AUTHORIZE_URL, ATLASSIAN_ME_URL, ATLASSIAN_RESOURCES_URL, ATLASSIAN_TOKEN_URL, CONFLUENCE_CALLBACK_PATH, CONFLUENCE_OAUTH_STATE_TTL_SECONDS, CONFLUENCE_SCOPES
from .http import confluence_client_id, confluence_client_secret, is_confluence_configured, json_request, safe_json_request
from .serializers import public_connection, public_site


def create_confluence_oauth_state() -> str:
    return token_urlsafe(24)


def confluence_callback_url() -> str:
    configured = os.getenv("CONFLUENCE_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{APP_BASE_URL.rstrip('/')}{CONFLUENCE_CALLBACK_PATH}"


def build_confluence_authorize_url(state: str) -> str:
    params = {
        "audience": "api.atlassian.com",
        "client_id": confluence_client_id(),
        "scope": CONFLUENCE_SCOPES,
        "redirect_uri": confluence_callback_url(),
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"{ATLASSIAN_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_confluence_code_for_connection(user_id: str, code: str) -> dict:
    token_payload = json_request(
        ATLASSIAN_TOKEN_URL,
        method="POST",
        body={
            "grant_type": "authorization_code",
            "client_id": confluence_client_id(),
            "client_secret": confluence_client_secret(),
            "code": code,
            "redirect_uri": confluence_callback_url(),
        },
    )
    access_token = required_str(token_payload, "access_token")
    refresh_token = required_str(token_payload, "refresh_token")
    profile = safe_json_request(ATLASSIAN_ME_URL, token=access_token) or {}
    resources = fetch_accessible_resources(access_token)

    with session_scope() as session:
        connection = session.scalar(select(ConfluenceUserConnection).where(ConfluenceUserConnection.user_id == user_id))
        if connection is None:
            connection = ConfluenceUserConnection(user_id=user_id, access_token_encrypted=encrypt_token(access_token), refresh_token_encrypted=encrypt_token(refresh_token))
            session.add(connection)
        connection.atlassian_account_id = optional_str(profile.get("account_id"))
        connection.account_email = optional_str(profile.get("email"))
        connection.account_name = optional_str(profile.get("name"))
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.refresh_token_encrypted = encrypt_token(refresh_token)
        connection.scopes = str(token_payload.get("scope") or CONFLUENCE_SCOPES)
        connection.expires_at = expires_at(token_payload.get("expires_in"))
        connection.updated_at = utc_now()
        replace_user_sites(session, user_id, resources)
        session.flush()
        return public_connection(connection, [resource_to_site(resource) for resource in resources])


def get_confluence_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(ConfluenceUserConnection).where(ConfluenceUserConnection.user_id == user_id))
        if connection is None:
            return {"connected": False, "configured": is_confluence_configured(), "sites": []}
        sites = session.scalars(select(ConfluenceUserSite).where(ConfluenceUserSite.user_id == user_id).order_by(ConfluenceUserSite.site_name.asc())).all()
        return public_connection(connection, [public_site(site) for site in sites])


def disconnect_confluence(user_id: str, remove_data: bool = False) -> dict:
    with session_scope() as session:
        if remove_data:
            source_ids = select(WorkspaceConfluenceSource.source_id).where(WorkspaceConfluenceSource.sync_owner_user_id == user_id)
            session.execute(delete(ConfluenceIndexedItem).where(ConfluenceIndexedItem.source_id.in_(source_ids)))
            session.execute(delete(WorkspaceConfluenceSource).where(WorkspaceConfluenceSource.sync_owner_user_id == user_id))
        session.execute(delete(ConfluenceUserConnection).where(ConfluenceUserConnection.user_id == user_id))
        session.execute(delete(ConfluenceUserSite).where(ConfluenceUserSite.user_id == user_id))
        session.execute(delete(ConfluenceVisibilityCache).where(ConfluenceVisibilityCache.user_id == user_id))
    return {"connected": False, "configured": is_confluence_configured(), "sites": []}


def get_valid_confluence_access_token(user_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(select(ConfluenceUserConnection).where(ConfluenceUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Confluence before using Confluence sources.")
        if connection.expires_at and as_utc(connection.expires_at) > utc_now() + timedelta(seconds=60):
            return decrypt_token(connection.access_token_encrypted)
        refresh_token = decrypt_token(connection.refresh_token_encrypted)

    payload = json_request(
        ATLASSIAN_TOKEN_URL,
        method="POST",
        body={"grant_type": "refresh_token", "client_id": confluence_client_id(), "client_secret": confluence_client_secret(), "refresh_token": refresh_token},
    )
    access_token = required_str(payload, "access_token")
    next_refresh = str(payload.get("refresh_token") or refresh_token)
    with session_scope() as session:
        connection = session.scalar(select(ConfluenceUserConnection).where(ConfluenceUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Confluence before using Confluence sources.")
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.refresh_token_encrypted = encrypt_token(next_refresh)
        connection.expires_at = expires_at(payload.get("expires_in"))
        connection.scopes = str(payload.get("scope") or connection.scopes)
        connection.updated_at = utc_now()
    return access_token


def fetch_accessible_resources(access_token: str) -> list[dict]:
    data = json_request(ATLASSIAN_RESOURCES_URL, token=access_token)
    return data if isinstance(data, list) else []


def replace_user_sites(session, user_id: str, resources: list[dict]) -> None:
    session.execute(delete(ConfluenceUserSite).where(ConfluenceUserSite.user_id == user_id))
    for resource in resources:
        site = resource_to_site(resource)
        if site["cloud_id"] and site["name"] and site["url"]:
            session.add(ConfluenceUserSite(user_id=user_id, cloud_id=site["cloud_id"], site_name=site["name"], site_url=site["url"], scopes=" ".join(site["scopes"]), avatar_url=site["avatar_url"]))


def resource_to_site(resource: dict) -> dict:
    return {"cloud_id": optional_str(resource.get("id")) or "", "name": optional_str(resource.get("name")) or "", "url": optional_str(resource.get("url")) or "", "scopes": list_str(resource.get("scopes")), "avatar_url": optional_str(resource.get("avatarUrl"))}


def expires_at(expires_in: object) -> object:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return utc_now() + timedelta(seconds=seconds)


def required_str(payload: dict, key: str) -> str:
    value = str(payload.get(key) or "")
    if not value:
        raise ValidationError(f"Confluence OAuth response is missing {key}.")
    return value


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def list_str(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []
