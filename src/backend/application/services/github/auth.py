from __future__ import annotations

import os
import urllib.parse
from secrets import token_urlsafe
from typing import Any

from sqlalchemy import delete, select

from src.backend.application.services.auth_service import APP_BASE_URL
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import GithubUserConnection, utc_now

from .constants import GITHUB_AUTHORIZE_URL, GITHUB_CALLBACK_PATH, GITHUB_SCOPES, GITHUB_TOKEN_URL
from .http import github_client_id, github_client_secret, github_form_request, github_json_request, is_github_configured
from src.backend.application.services.jira.crypto import decrypt_token, encrypt_token


def create_github_oauth_state() -> str:
    return token_urlsafe(24)


def github_callback_url() -> str:
    configured = os.getenv("GITHUB_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{APP_BASE_URL.rstrip('/')}{GITHUB_CALLBACK_PATH}"


def build_github_authorize_url(state: str) -> str:
    params = {
        "client_id": github_client_id(),
        "redirect_uri": github_callback_url(),
        "scope": GITHUB_SCOPES,
        "state": state,
        "allow_signup": "true",
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_github_code_for_connection(user_id: str, code: str) -> dict:
    payload = {
        "client_id": github_client_id(),
        "client_secret": github_client_secret(),
        "code": code,
        "redirect_uri": github_callback_url(),
    }
    token_payload = github_form_request(GITHUB_TOKEN_URL, payload)
    access_token = str(token_payload.get("access_token") or "")
    if not access_token:
        raise ValidationError("GitHub OAuth response is missing access_token.")
    scopes = str(token_payload.get("scope") or GITHUB_SCOPES)
    profile = github_json_request("/user", token=access_token)

    with session_scope() as session:
        connection = session.scalar(select(GithubUserConnection).where(GithubUserConnection.user_id == user_id))
        if connection is None:
            connection = GithubUserConnection(user_id=user_id, access_token_encrypted=encrypt_token(access_token))
            session.add(connection)
        connection.github_user_id = optional_str(profile.get("id"))
        connection.login = optional_str(profile.get("login"))
        connection.name = optional_str(profile.get("name"))
        connection.avatar_url = optional_str(profile.get("avatar_url"))
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.scopes = scopes
        connection.updated_at = utc_now()
        session.flush()
        return public_connection(connection)


def get_github_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(GithubUserConnection).where(GithubUserConnection.user_id == user_id))
        if connection is None:
            return {"connected": False, "configured": is_github_configured()}
        return public_connection(connection)


def disconnect_github(user_id: str) -> dict:
    with session_scope() as session:
        session.execute(delete(GithubUserConnection).where(GithubUserConnection.user_id == user_id))
    return {"connected": False}


def get_valid_github_access_token(user_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(select(GithubUserConnection).where(GithubUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect GitHub before using GitHub repositories.")
        return decrypt_token(connection.access_token_encrypted)


def public_connection(connection: GithubUserConnection) -> dict:
    return {
        "connected": True,
        "configured": is_github_configured(),
        "github_user_id": connection.github_user_id,
        "login": connection.login,
        "name": connection.name,
        "avatar_url": connection.avatar_url,
        "scopes": scopes_list(connection.scopes or ""),
    }


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def scopes_list(value: str) -> list[str]:
    return [scope for scope in value.replace(",", " ").split() if scope]
