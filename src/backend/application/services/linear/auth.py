from __future__ import annotations

import os
import urllib.parse
from secrets import token_urlsafe
from typing import Any

from sqlalchemy import delete, select

from src.backend.application.services.auth_service import APP_BASE_URL
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.application.services.jira.crypto import decrypt_token, encrypt_token
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import LinearUserConnection, LinearVisibilityCache, utc_now

from .constants import LINEAR_AUTHORIZE_URL, LINEAR_CALLBACK_PATH, LINEAR_OAUTH_STATE_TTL_SECONDS, LINEAR_SCOPES, LINEAR_TOKEN_URL
from .http import is_linear_configured, linear_client_id, linear_client_secret, linear_form_request, linear_graphql_request
from .serializers import public_connection


def create_linear_oauth_state() -> str:
    return token_urlsafe(24)


def linear_callback_url() -> str:
    configured = os.getenv("LINEAR_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{APP_BASE_URL.rstrip('/')}{LINEAR_CALLBACK_PATH}"


def build_linear_authorize_url(state: str) -> str:
    params = {
        "client_id": linear_client_id(),
        "redirect_uri": linear_callback_url(),
        "response_type": "code",
        "scope": LINEAR_SCOPES,
        "state": state,
        "prompt": "consent",
    }
    return f"{LINEAR_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_linear_code_for_connection(user_id: str, code: str) -> dict:
    token_payload = linear_form_request(
        LINEAR_TOKEN_URL,
        {
            "client_id": linear_client_id(),
            "client_secret": linear_client_secret(),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": linear_callback_url(),
        },
    )
    access_token = str(token_payload.get("access_token") or "")
    if not access_token:
        raise ValidationError("Linear OAuth response is missing access_token.")
    profile = fetch_linear_profile(access_token)

    with session_scope() as session:
        connection = session.scalar(select(LinearUserConnection).where(LinearUserConnection.user_id == user_id))
        if connection is None:
            connection = LinearUserConnection(user_id=user_id, access_token_encrypted=encrypt_token(access_token))
            session.add(connection)
        connection.linear_user_id = optional_str(profile.get("id"))
        organization = profile.get("organization") if isinstance(profile.get("organization"), dict) else {}
        connection.workspace_id = optional_str(organization.get("id"))
        connection.workspace_name = optional_str(organization.get("name"))
        connection.name = optional_str(profile.get("name"))
        connection.email = optional_str(profile.get("email"))
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.scopes = str(token_payload.get("scope") or LINEAR_SCOPES)
        connection.updated_at = utc_now()
        session.flush()
        return public_connection(connection)


def fetch_linear_profile(token: str) -> dict:
    data = linear_graphql_request(
        "query { viewer { id name email organization { id name } } }",
        token,
    )
    return data.get("viewer", {}) if isinstance(data.get("viewer"), dict) else {}


def get_linear_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(LinearUserConnection).where(LinearUserConnection.user_id == user_id))
        if connection is None:
            return {"connected": False, "configured": is_linear_configured()}
        return public_connection(connection)


def disconnect_linear(user_id: str) -> dict:
    with session_scope() as session:
        session.execute(delete(LinearUserConnection).where(LinearUserConnection.user_id == user_id))
        session.execute(delete(LinearVisibilityCache).where(LinearVisibilityCache.user_id == user_id))
    return {"connected": False, "configured": is_linear_configured()}


def get_valid_linear_access_token(user_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(select(LinearUserConnection).where(LinearUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Linear before using Linear sources.")
        return decrypt_token(connection.access_token_encrypted)


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
