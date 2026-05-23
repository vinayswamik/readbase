from __future__ import annotations

import base64
import json
import os
import urllib.parse
from datetime import timedelta
from secrets import token_urlsafe

from sqlalchemy import delete, select

from src.backend.application.services.auth_service import APP_BASE_URL
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.application.services.jira.crypto import decrypt_token, encrypt_token
from src.backend.application.services.jira.utils import as_utc
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import TeamsUserConnection, utc_now

from .constants import MICROSOFT_AUTHORIZE_URL, MICROSOFT_TOKEN_URL, TEAMS_CALLBACK_PATH, TEAMS_OAUTH_SCOPES
from .http import is_teams_configured, microsoft_client_id, microsoft_client_secret, teams_form_request, teams_json_request
from .serializers import optional_str, public_connection, public_team


def create_teams_oauth_state() -> str:
    return token_urlsafe(24)


def teams_callback_url() -> str:
    configured = os.getenv("MICROSOFT_TEAMS_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{APP_BASE_URL.rstrip('/')}{TEAMS_CALLBACK_PATH}"


def build_teams_authorize_url(state: str) -> str:
    params = {
        "client_id": microsoft_client_id(),
        "response_type": "code",
        "redirect_uri": teams_callback_url(),
        "response_mode": "query",
        "scope": TEAMS_OAUTH_SCOPES,
        "state": state,
        "prompt": "select_account",
    }
    return f"{MICROSOFT_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_teams_code_for_connection(user_id: str, code: str) -> dict:
    token_payload = teams_form_request(
        MICROSOFT_TOKEN_URL,
        {
            "client_id": microsoft_client_id(),
            "client_secret": microsoft_client_secret(),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": teams_callback_url(),
            "scope": TEAMS_OAUTH_SCOPES,
        },
    )
    access_token = str(token_payload.get("access_token") or "")
    if not access_token:
        raise ValidationError("Microsoft OAuth response is missing access_token.")

    profile = fetch_teams_profile(access_token)
    teams = fetch_joined_teams(access_token)
    tenant_id = tenant_id_from_id_token(optional_str(token_payload.get("id_token")))

    with session_scope() as session:
        connection = session.scalar(select(TeamsUserConnection).where(TeamsUserConnection.user_id == user_id))
        if connection is None:
            connection = TeamsUserConnection(user_id=user_id, access_token_encrypted=encrypt_token(access_token))
            session.add(connection)
        connection.microsoft_user_id = optional_str(profile.get("id"))
        connection.tenant_id = tenant_id
        connection.display_name = optional_str(profile.get("displayName"))
        connection.user_principal_name = optional_str(profile.get("userPrincipalName"))
        connection.mail = optional_str(profile.get("mail"))
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.refresh_token_encrypted = encrypt_token(str(token_payload["refresh_token"])) if token_payload.get("refresh_token") else None
        connection.scopes = str(token_payload.get("scope") or TEAMS_OAUTH_SCOPES)
        connection.expires_at = expires_at(token_payload.get("expires_in"))
        connection.updated_at = utc_now()
        session.flush()
        return public_connection(connection, teams)


def fetch_teams_profile(access_token: str) -> dict:
    payload = teams_json_request("/me", access_token)
    return payload if isinstance(payload, dict) else {}


def fetch_joined_teams(access_token: str) -> list[dict]:
    payload = teams_json_request("/me/joinedTeams", access_token)
    values = payload.get("value") if isinstance(payload, dict) else []
    if not isinstance(values, list):
        return []
    return [team for team in (public_team(item) for item in values if isinstance(item, dict)) if team["team_id"]]


def get_teams_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(TeamsUserConnection).where(TeamsUserConnection.user_id == user_id))
        if connection is None:
            return {"connected": False, "configured": is_teams_configured(), "teams": []}
        return public_connection(connection, [])


def disconnect_teams(user_id: str, remove_data: bool = False) -> dict:
    with session_scope() as session:
        session.execute(delete(TeamsUserConnection).where(TeamsUserConnection.user_id == user_id))
    return {"connected": False, "configured": is_teams_configured(), "teams": []}


def get_valid_teams_access_token(user_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(select(TeamsUserConnection).where(TeamsUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Microsoft Teams before using Teams sources.")
        if connection.expires_at and as_utc(connection.expires_at) > utc_now() + timedelta(seconds=60):
            return decrypt_token(connection.access_token_encrypted)
        if not connection.refresh_token_encrypted:
            raise PermissionDeniedError("Reconnect Microsoft Teams to refresh this token.")
        refresh_token = decrypt_token(connection.refresh_token_encrypted)

    payload = teams_form_request(
        MICROSOFT_TOKEN_URL,
        {
            "client_id": microsoft_client_id(),
            "client_secret": microsoft_client_secret(),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": TEAMS_OAUTH_SCOPES,
        },
    )
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise PermissionDeniedError("Reconnect Microsoft Teams to refresh this token.")
    with session_scope() as session:
        connection = session.scalar(select(TeamsUserConnection).where(TeamsUserConnection.user_id == user_id))
        if connection is not None:
            connection.access_token_encrypted = encrypt_token(access_token)
            connection.refresh_token_encrypted = encrypt_token(str(payload["refresh_token"])) if payload.get("refresh_token") else connection.refresh_token_encrypted
            connection.scopes = str(payload.get("scope") or connection.scopes)
            connection.expires_at = expires_at(payload.get("expires_in"))
            connection.updated_at = utc_now()
    return access_token


def expires_at(expires_in: object) -> object:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return utc_now() + timedelta(seconds=seconds)


def tenant_id_from_id_token(id_token: str | None) -> str | None:
    if not id_token:
        return None
    try:
        parts = id_token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
        return optional_str(data.get("tid"))
    except Exception:
        return None
