from __future__ import annotations

import os
import urllib.parse
from datetime import timedelta
from secrets import token_urlsafe

from sqlalchemy import delete, select

from src.backend.application.services.auth_service import APP_BASE_URL
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import JiraUserConnection, JiraUserSite, JiraVisibilityCache, utc_now

from .constants import (
    ATLASSIAN_AUTHORIZE_URL,
    ATLASSIAN_ME_URL,
    ATLASSIAN_RESOURCES_URL,
    ATLASSIAN_TOKEN_URL,
    JIRA_CALLBACK_PATH,
    JIRA_SCOPES,
)
from .crypto import decrypt_token, encrypt_token
from .http import jira_client_id, jira_client_secret, json_request, safe_json_request
from .serializers import public_connection, public_site, public_sites_for_resources
from .utils import as_utc, expires_at, list_str, optional_str, required_str


def create_jira_oauth_state() -> str:
    return token_urlsafe(24)


def jira_callback_url() -> str:
    configured = os.getenv("JIRA_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{APP_BASE_URL.rstrip('/')}{JIRA_CALLBACK_PATH}"


def build_jira_authorize_url(state: str) -> str:
    params = {
        "audience": "api.atlassian.com",
        "client_id": jira_client_id(),
        "scope": JIRA_SCOPES,
        "redirect_uri": jira_callback_url(),
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"{ATLASSIAN_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_jira_code_for_connection(user_id: str, code: str) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "client_id": jira_client_id(),
        "client_secret": jira_client_secret(),
        "code": code,
        "redirect_uri": jira_callback_url(),
    }
    token_payload = json_request(ATLASSIAN_TOKEN_URL, method="POST", body=payload)
    access_token = required_str(token_payload, "access_token")
    refresh_token = required_str(token_payload, "refresh_token")
    token_expires_at = expires_at(token_payload.get("expires_in"))
    scopes = str(token_payload.get("scope") or JIRA_SCOPES)
    profile = safe_json_request(ATLASSIAN_ME_URL, token=access_token) or {}
    resources = fetch_accessible_resources(access_token)

    with session_scope() as session:
        connection = session.scalar(select(JiraUserConnection).where(JiraUserConnection.user_id == user_id))
        if connection is None:
            connection = JiraUserConnection(
                user_id=user_id,
                access_token_encrypted=encrypt_token(access_token),
                refresh_token_encrypted=encrypt_token(refresh_token),
            )
            session.add(connection)
        connection.atlassian_account_id = optional_str(profile.get("account_id"))
        connection.account_email = optional_str(profile.get("email"))
        connection.account_name = optional_str(profile.get("name"))
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.refresh_token_encrypted = encrypt_token(refresh_token)
        connection.scopes = scopes
        connection.expires_at = token_expires_at
        connection.updated_at = utc_now()

        replace_user_sites(session, user_id, resources)
        session.flush()
        return public_connection(connection, public_sites_for_resources(resources))


def get_jira_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(JiraUserConnection).where(JiraUserConnection.user_id == user_id))
        if connection is None:
            return {"connected": False, "sites": []}
        sites = session.scalars(
            select(JiraUserSite).where(JiraUserSite.user_id == user_id).order_by(JiraUserSite.site_name.asc())
        ).all()
        return public_connection(connection, [public_site(site) for site in sites])


def disconnect_jira(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(JiraUserConnection).where(JiraUserConnection.user_id == user_id))
        if connection is not None:
            session.delete(connection)
        session.execute(delete(JiraUserSite).where(JiraUserSite.user_id == user_id))
        session.execute(delete(JiraVisibilityCache).where(JiraVisibilityCache.user_id == user_id))
    return {"connected": False, "sites": []}


def get_valid_jira_access_token(user_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(select(JiraUserConnection).where(JiraUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Jira before using Jira sources.")
        if connection.expires_at and as_utc(connection.expires_at) > utc_now() + timedelta(seconds=60):
            return decrypt_token(connection.access_token_encrypted)
        refresh_token = decrypt_token(connection.refresh_token_encrypted)

    payload = {
        "grant_type": "refresh_token",
        "client_id": jira_client_id(),
        "client_secret": jira_client_secret(),
        "refresh_token": refresh_token,
    }
    token_payload = json_request(ATLASSIAN_TOKEN_URL, method="POST", body=payload)
    access_token = required_str(token_payload, "access_token")
    next_refresh_token = str(token_payload.get("refresh_token") or refresh_token)

    with session_scope() as session:
        connection = session.scalar(select(JiraUserConnection).where(JiraUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Jira before using Jira sources.")
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.refresh_token_encrypted = encrypt_token(next_refresh_token)
        connection.expires_at = expires_at(token_payload.get("expires_in"))
        connection.scopes = str(token_payload.get("scope") or connection.scopes)
        connection.updated_at = utc_now()
    return access_token


def replace_user_sites(session, user_id: str, resources: list[dict]) -> None:
    session.execute(delete(JiraUserSite).where(JiraUserSite.user_id == user_id))
    for resource in resources:
        cloud_id = optional_str(resource.get("id"))
        name = optional_str(resource.get("name"))
        url = optional_str(resource.get("url"))
        if not cloud_id or not name or not url:
            continue
        session.add(
            JiraUserSite(
                user_id=user_id,
                cloud_id=cloud_id,
                site_name=name,
                site_url=url,
                scopes=" ".join(list_str(resource.get("scopes"))),
                avatar_url=optional_str(resource.get("avatarUrl")),
            )
        )


def fetch_accessible_resources(access_token: str) -> list[dict]:
    data = json_request(ATLASSIAN_RESOURCES_URL, token=access_token)
    return data if isinstance(data, list) else []
