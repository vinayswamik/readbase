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
from src.backend.infrastructure.models import NotionIndexedItem, NotionUserConnection, NotionVisibilityCache, WorkspaceNotionSource, utc_now

from .constants import NOTION_AUTHORIZE_URL, NOTION_CALLBACK_PATH, NOTION_TOKEN_URL
from .http import is_notion_configured, json_request, notion_client_id, notion_client_secret
from .serializers import public_connection


def create_notion_oauth_state() -> str:
    return token_urlsafe(24)


def notion_callback_url() -> str:
    configured = os.getenv("NOTION_REDIRECT_URI", "").strip()
    if configured:
        require_https_redirect_uri(configured)
        return configured
    url = f"{notion_public_base_url()}{NOTION_CALLBACK_PATH}"
    require_https_redirect_uri(url)
    return url


def notion_public_base_url() -> str:
    """Public origin for Notion OAuth (must be https)."""
    override = os.getenv("NOTION_PUBLIC_BASE_URL", "").strip()
    if override:
        return override.rstrip("/")
    base = APP_BASE_URL.rstrip("/")
    if base.startswith("http://") and os.getenv("READBASE_SSL_CERTFILE", "").strip():
        return f"https://{base[len('http://'):]}"
    return base


def require_https_redirect_uri(url: str) -> None:
    if not url.lower().startswith("https://"):
        raise ValidationError(
            "Notion requires an HTTPS redirect URI. Set NOTION_REDIRECT_URI to an https callback "
            "(e.g. https://127.0.0.1:8000/api/me/integrations/notion/callback with local SSL, or an ngrok URL)."
        )


def build_notion_authorize_url(state: str) -> str:
    params = {
        "client_id": notion_client_id(),
        "response_type": "code",
        "owner": "user",
        "redirect_uri": notion_callback_url(),
        "state": state,
    }
    return f"{NOTION_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_notion_code_for_connection(user_id: str, code: str) -> dict:
    token_payload = json_request(
        NOTION_TOKEN_URL,
        method="POST",
        basic_auth=(notion_client_id(), notion_client_secret()),
        body={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": notion_callback_url(),
        },
    )
    access_token = required_str(token_payload, "access_token")
    owner = token_payload.get("owner") if isinstance(token_payload.get("owner"), dict) else {}
    owner_user = owner.get("user") if isinstance(owner.get("user"), dict) else {}
    owner_workspace = owner.get("workspace") if isinstance(owner.get("workspace"), dict) else {}
    owner_type = optional_str(owner.get("type"))
    owner_name = optional_str(owner_user.get("name")) or optional_str(owner_workspace.get("name"))
    workspace_icon_payload = token_payload.get("workspace_icon")
    workspace_icon = optional_str(workspace_icon_payload.get("url")) if isinstance(workspace_icon_payload, dict) else optional_str(workspace_icon_payload)

    with session_scope() as session:
        connection = session.scalar(select(NotionUserConnection).where(NotionUserConnection.user_id == user_id))
        if connection is None:
            connection = NotionUserConnection(user_id=user_id, access_token_encrypted=encrypt_token(access_token))
            session.add(connection)
        connection.notion_workspace_id = optional_str(token_payload.get("workspace_id"))
        connection.workspace_name = optional_str(token_payload.get("workspace_name"))
        connection.workspace_icon = workspace_icon
        connection.bot_id = optional_str(token_payload.get("bot_id"))
        connection.owner_type = owner_type
        connection.owner_name = owner_name
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.updated_at = utc_now()
        session.flush()
        return public_connection(connection)


def get_notion_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(NotionUserConnection).where(NotionUserConnection.user_id == user_id))
        if connection is None:
            return {"connected": False, "configured": is_notion_configured()}
        return public_connection(connection)


def disconnect_notion(user_id: str, remove_data: bool = False) -> dict:
    with session_scope() as session:
        if remove_data:
            source_ids = select(WorkspaceNotionSource.source_id).where(WorkspaceNotionSource.sync_owner_user_id == user_id)
            session.execute(delete(NotionIndexedItem).where(NotionIndexedItem.source_id.in_(source_ids)))
            session.execute(delete(WorkspaceNotionSource).where(WorkspaceNotionSource.sync_owner_user_id == user_id))
        session.execute(delete(NotionUserConnection).where(NotionUserConnection.user_id == user_id))
        session.execute(delete(NotionVisibilityCache).where(NotionVisibilityCache.user_id == user_id))
    return {"connected": False, "configured": is_notion_configured()}


def get_valid_notion_access_token(user_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(select(NotionUserConnection).where(NotionUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Notion before using Notion sources.")
        return decrypt_token(connection.access_token_encrypted)


def required_str(payload: dict, key: str) -> str:
    value = str(payload.get(key) or "")
    if not value:
        raise ValidationError(f"Notion OAuth response is missing {key}.")
    return value


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
