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
from src.backend.infrastructure.models import BitbucketUserConnection, utc_now

from .constants import BITBUCKET_AUTHORIZE_URL, BITBUCKET_CALLBACK_PATH, BITBUCKET_OAUTH_STATE_TTL_SECONDS, BITBUCKET_SCOPES, BITBUCKET_TOKEN_URL
from .http import bitbucket_client_id, bitbucket_form_request, bitbucket_json_request, is_bitbucket_configured


def create_bitbucket_oauth_state() -> str:
    return token_urlsafe(24)


def bitbucket_callback_url() -> str:
    configured = os.getenv("BITBUCKET_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{APP_BASE_URL.rstrip('/')}{BITBUCKET_CALLBACK_PATH}"


def build_bitbucket_authorize_url(state: str) -> str:
    params = {
        "client_id": bitbucket_client_id(),
        "response_type": "code",
        "redirect_uri": bitbucket_callback_url(),
        "scope": BITBUCKET_SCOPES,
        "state": state,
    }
    return f"{BITBUCKET_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_bitbucket_code_for_connection(user_id: str, code: str) -> dict:
    token_payload = bitbucket_form_request(
        BITBUCKET_TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": bitbucket_callback_url(),
        },
    )
    access_token = str(token_payload.get("access_token") or "")
    if not access_token:
        raise ValidationError("Bitbucket OAuth response is missing access_token.")
    refresh_token = optional_str(token_payload.get("refresh_token"))
    scopes = str(token_payload.get("scopes") or token_payload.get("scope") or BITBUCKET_SCOPES)
    profile = bitbucket_json_request("/user", token=access_token)
    links = profile.get("links") if isinstance(profile.get("links"), dict) else {}
    avatar = links.get("avatar") if isinstance(links.get("avatar"), dict) else {}

    with session_scope() as session:
        connection = session.scalar(select(BitbucketUserConnection).where(BitbucketUserConnection.user_id == user_id))
        if connection is None:
            connection = BitbucketUserConnection(user_id=user_id, access_token_encrypted=encrypt_token(access_token))
            session.add(connection)
        connection.bitbucket_account_id = optional_str(profile.get("account_id") or profile.get("uuid"))
        connection.username = optional_str(profile.get("username") or profile.get("nickname"))
        connection.display_name = optional_str(profile.get("display_name"))
        connection.avatar_url = optional_str(avatar.get("href"))
        connection.access_token_encrypted = encrypt_token(access_token)
        connection.refresh_token_encrypted = encrypt_token(refresh_token) if refresh_token else None
        connection.scopes = scopes
        connection.expires_at = expires_at(token_payload.get("expires_in"))
        connection.updated_at = utc_now()
        session.flush()
        return public_connection(connection)


def get_bitbucket_connection_status(user_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(select(BitbucketUserConnection).where(BitbucketUserConnection.user_id == user_id))
        if connection is None:
            return {"connected": False, "configured": is_bitbucket_configured()}
        return public_connection(connection)


def disconnect_bitbucket(user_id: str) -> dict:
    with session_scope() as session:
        session.execute(delete(BitbucketUserConnection).where(BitbucketUserConnection.user_id == user_id))
    return {"connected": False, "configured": is_bitbucket_configured()}


def get_valid_bitbucket_access_token(user_id: str) -> str:
    with session_scope() as session:
        connection = session.scalar(select(BitbucketUserConnection).where(BitbucketUserConnection.user_id == user_id))
        if connection is None:
            raise PermissionDeniedError("Connect Bitbucket before using Bitbucket repositories.")
        if connection.expires_at and as_utc(connection.expires_at) <= utc_now() + timedelta(seconds=60):
            raise PermissionDeniedError("Reconnect Bitbucket to refresh this token.")
        return decrypt_token(connection.access_token_encrypted)


def public_connection(connection: BitbucketUserConnection) -> dict:
    return {
        "connected": True,
        "configured": is_bitbucket_configured(),
        "bitbucket_account_id": connection.bitbucket_account_id,
        "username": connection.username,
        "display_name": connection.display_name,
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
