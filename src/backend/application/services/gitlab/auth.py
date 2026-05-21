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
from src.backend.infrastructure.models import GitlabUserConnection, utc_now

from .constants import GITLAB_AUTHORIZE_URL, GITLAB_CALLBACK_PATH, GITLAB_OAUTH_STATE_TTL_SECONDS, GITLAB_SCOPES, GITLAB_TOKEN_URL
from .http import gitlab_client_id, gitlab_client_secret, gitlab_form_request, gitlab_json_request, is_gitlab_configured


def create_gitlab_oauth_state() -> str:
    return token_urlsafe(24)


def gitlab_callback_url() -> str:
    configured = os.getenv("GITLAB_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{APP_BASE_URL.rstrip('/')}{GITLAB_CALLBACK_PATH}"


def build_gitlab_authorize_url(state: str) -> str:
    params = {
        "client_id": gitlab_client_id(),
        "redirect_uri": gitlab_callback_url(),
        "response_type": "code",
        "scope": GITLAB_SCOPES,
        "state": state,
    }
    return f"{GITLAB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_gitlab_code_for_connection(user_id: str, code: str) -> dict:
    token_payload = gitlab_form_request(
        GITLAB_TOKEN_URL,
        {
            "client_id": gitlab_client_id(),
            "client_secret": gitlab_client_secret(),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": gitlab_callback_url(),
        },
    )
    access_token = str(token_payload.get("access_token") or "")
    if not access_token:
        raise ValidationError("GitLab OAuth response is missing access_token.")
    profile = fetch_gitlab_profile(access_token)
    scopes = str(token_payload.get("scope") or GITLAB_SCOPES)

    with session_scope() as session:
        connection = session.scalar(select(GitlabUserConnection).where(GitlabUserConnection.user_id == user_id))
        if connection is None:
            connection = GitlabUserConnection(user_id=user_id, access_token_encrypted=encrypt_token(access_token))
            session.add(connection)
        connection.gitlab_user_id = optional_str(profile.get("id"))
        connection.username = optional_str(profile.get("username"))
        connection.name = optional_str(profile.get("name"))
        connection.avatar_url = optional_str(profile.get("avatar_url"))
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.refresh_token_encrypted = encrypt_token(str(token_payload["refresh_token"])) if token_payload.get("refresh_token") else None
        connection.scopes = scopes
        connection.expires_at = expires_at(token_payload.get("expires_in"))
        connection.updated_at = utc_now()
        session.flush()
        return public_connection(connection)


def get_gitlab_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(GitlabUserConnection).where(GitlabUserConnection.user_id == user_id))
        if connection is None:
            return {"connected": False, "configured": is_gitlab_configured()}
        return public_connection(connection)


def fetch_gitlab_profile(access_token: str) -> dict:
    try:
        profile = gitlab_json_request("/user", token=access_token)
    except Exception:
        return {}
    return profile if isinstance(profile, dict) else {}


def disconnect_gitlab(user_id: str) -> dict:
    with session_scope() as session:
        session.execute(delete(GitlabUserConnection).where(GitlabUserConnection.user_id == user_id))
    return {"connected": False, "configured": is_gitlab_configured()}


def get_valid_gitlab_access_token(user_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(select(GitlabUserConnection).where(GitlabUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect GitLab before using GitLab projects.")
        if connection.expires_at and as_utc(connection.expires_at) <= utc_now() + timedelta(seconds=60):
            raise PermissionDeniedError("Reconnect GitLab to refresh this token.")
        return decrypt_token(connection.access_token_encrypted)


def public_connection(connection: GitlabUserConnection) -> dict:
    return {
        "connected": True,
        "configured": is_gitlab_configured(),
        "gitlab_user_id": connection.gitlab_user_id,
        "username": connection.username,
        "name": connection.name,
        "avatar_url": connection.avatar_url,
        "scopes": scopes_list(connection.scopes or ""),
    }


def expires_at(expires_in: object) -> object:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return utc_now() + timedelta(seconds=seconds)


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def scopes_list(value: str) -> list[str]:
    return [scope for scope in value.replace(",", " ").split() if scope]
