from __future__ import annotations

import os
import urllib.parse
from datetime import timedelta
from secrets import token_urlsafe

from sqlalchemy import delete, select

from src.backend.application.services.auth_service import APP_BASE_URL
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.application.services.jira.crypto import decrypt_token, encrypt_token
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import SlackIndexedItem, SlackUserConnection, SlackVisibilityCache, WorkspaceSlackSource, utc_now

from .constants import SLACK_AUTHORIZE_URL, SLACK_CALLBACK_PATH, SLACK_OAUTH_STATE_TTL_SECONDS, SLACK_USER_SCOPES
from .http import is_slack_configured, slack_api_request, slack_client_id, slack_client_secret, slack_oauth_request
from .serializers import public_connection, public_team
from .utils import as_utc, optional_str


def create_slack_oauth_state() -> str:
    return token_urlsafe(24)


def slack_callback_url() -> str:
    configured = os.getenv("SLACK_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{APP_BASE_URL.rstrip('/')}{SLACK_CALLBACK_PATH}"


def build_slack_authorize_url(state: str) -> str:
    params = {
        "client_id": slack_client_id(),
        "user_scope": SLACK_USER_SCOPES,
        "redirect_uri": slack_callback_url(),
        "state": state,
    }
    return f"{SLACK_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_slack_code_for_connection(user_id: str, code: str) -> dict:
    payload = {
        "client_id": slack_client_id(),
        "client_secret": slack_client_secret(),
        "code": code,
        "redirect_uri": slack_callback_url(),
    }
    token_payload = slack_oauth_request(payload)
    authed_user = token_payload.get("authed_user") if isinstance(token_payload.get("authed_user"), dict) else {}
    access_token = str(authed_user.get("access_token") or "")
    if not access_token:
        raise ValidationError("Slack OAuth response is missing user access_token.")
    team = token_payload.get("team") if isinstance(token_payload.get("team"), dict) else {}
    team_id = str(team.get("id") or "")
    team_name = str(team.get("name") or "")
    if not team_id or not team_name:
        raise ValidationError("Slack OAuth response is missing team information.")
    team_domain = fetch_team_domain(access_token)

    with session_scope() as session:
        connection = session.scalar(
            select(SlackUserConnection).where(
                SlackUserConnection.user_id == user_id,
                SlackUserConnection.team_id == team_id,
            )
        )
        if connection is None:
            connection = SlackUserConnection(
                user_id=user_id,
                slack_user_id=str(authed_user.get("id") or ""),
                team_id=team_id,
                team_name=team_name,
                access_token_encrypted=encrypt_token(access_token),
            )
            session.add(connection)
        connection.slack_user_id = str(authed_user.get("id") or connection.slack_user_id)
        connection.team_name = team_name
        connection.team_domain = team_domain
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.refresh_token_encrypted = encrypt_token(str(authed_user["refresh_token"])) if authed_user.get("refresh_token") else None
        connection.scopes = str(authed_user.get("scope") or SLACK_USER_SCOPES)
        connection.expires_at = expires_at(authed_user.get("expires_in"))
        connection.updated_at = utc_now()
        session.flush()
        teams = [public_team(row) for row in session.scalars(select(SlackUserConnection).where(SlackUserConnection.user_id == user_id)).all()]
        return public_connection(teams)


def fetch_team_domain(access_token: str) -> str | None:
    try:
        payload = slack_api_request("/team.info", token=access_token)
    except Exception:
        return None
    team = payload.get("team") if isinstance(payload, dict) and isinstance(payload.get("team"), dict) else {}
    return optional_str(team.get("domain"))


def get_slack_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        teams = [
            public_team(connection)
            for connection in session.scalars(
                select(SlackUserConnection).where(SlackUserConnection.user_id == user_id).order_by(SlackUserConnection.team_name.asc())
            ).all()
        ]
    if not teams:
        return {"connected": False, "configured": is_slack_configured(), "teams": []}
    return public_connection(teams)


def disconnect_slack(user_id: str, team_id: str | None = None, remove_data: bool = False) -> dict:
    with session_scope() as session:
        if remove_data:
            source_statement = select(WorkspaceSlackSource.source_id).where(WorkspaceSlackSource.sync_owner_user_id == user_id)
            delete_sources_statement = delete(WorkspaceSlackSource).where(WorkspaceSlackSource.sync_owner_user_id == user_id)
            if team_id:
                normalized_team_id = team_id.strip()
                source_statement = source_statement.where(WorkspaceSlackSource.team_id == normalized_team_id)
                delete_sources_statement = delete_sources_statement.where(WorkspaceSlackSource.team_id == normalized_team_id)
            session.execute(delete(SlackIndexedItem).where(SlackIndexedItem.source_id.in_(source_statement)))
            session.execute(delete_sources_statement)
        statement = delete(SlackUserConnection).where(SlackUserConnection.user_id == user_id)
        if team_id:
            statement = statement.where(SlackUserConnection.team_id == team_id.strip())
        session.execute(statement)
        cache_statement = delete(SlackVisibilityCache).where(SlackVisibilityCache.user_id == user_id)
        if team_id:
            cache_statement = cache_statement.where(SlackVisibilityCache.team_id == team_id.strip())
        session.execute(cache_statement)
    return get_slack_connection_status(user_id)


def get_valid_slack_access_token(user_id: str, team_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(
            select(SlackUserConnection).where(
                SlackUserConnection.user_id == user_id,
                SlackUserConnection.team_id == team_id,
            )
        )
        if connection is None:
            raise PermissionDeniedError("Connect Slack before using Slack channels.")
        if connection.expires_at and as_utc(connection.expires_at) <= utc_now() + timedelta(seconds=60):
            raise PermissionDeniedError("Reconnect Slack to refresh this token.")
        return decrypt_token(connection.access_token_encrypted)


def expires_at(expires_in: object) -> object:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return utc_now() + timedelta(seconds=seconds)
