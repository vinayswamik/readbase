from __future__ import annotations

import base64
import hashlib
import json
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
import secrets
from secrets import token_urlsafe

import certifi

from src.backend.application.services.exceptions import ValidationError

logger = logging.getLogger(__name__)
TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
DEFAULT_STATE_TTL_SECONDS = 600


def oauth_states_match(provided: str | None, expected: str | None) -> bool:
    if provided is None or expected is None:
        return False
    return secrets.compare_digest(provided, expected)


@dataclass(frozen=True)
class ConnectorOAuthConfig:
    connector_id: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    redirect_uri: str
    scopes: str
    supports_pkce: bool = True
    extra_authorize_params: dict[str, str] | None = None


@dataclass(frozen=True)
class ConnectorOAuthStart:
    state: str
    code_verifier: str | None


def create_connector_oauth_start(supports_pkce: bool) -> ConnectorOAuthStart:
    return ConnectorOAuthStart(
        state=token_urlsafe(24),
        code_verifier=token_urlsafe(48) if supports_pkce else None,
    )


def build_connector_authorize_url(config: ConnectorOAuthConfig, start: ConnectorOAuthStart) -> str:
    params: dict[str, str] = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": config.scopes,
        "state": start.state,
    }
    if config.supports_pkce and start.code_verifier:
        params["code_challenge"] = _pkce_challenge(start.code_verifier)
        params["code_challenge_method"] = "S256"
    if config.extra_authorize_params:
        params.update(config.extra_authorize_params)
    return f"{config.authorize_url}?{urllib.parse.urlencode(params)}"


def exchange_connector_code(config: ConnectorOAuthConfig, code: str, code_verifier: str | None) -> dict:
    from src.backend.application.services.auth.oauth_codes import consume_oauth_code

    if not consume_oauth_code(f"{config.connector_id}:{code}"):
        raise ValidationError(f"{config.connector_id} authorization code already used.")
    body: dict[str, str] = {
        "code": code,
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "redirect_uri": config.redirect_uri,
        "grant_type": "authorization_code",
    }
    if config.supports_pkce and code_verifier:
        body["code_verifier"] = code_verifier
    encoded = urllib.parse.urlencode(body).encode("utf-8")
    request = urllib.request.Request(
        config.token_url,
        data=encoded,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15, context=TLS_CONTEXT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _read_http_error(exc)
        raise ValidationError(f"{config.connector_id} token exchange failed: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValidationError(f"Unable to reach {config.connector_id} OAuth servers.") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid token response from {config.connector_id}.") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"Unexpected token response from {config.connector_id}.")
    if payload.get("error"):
        raise ValidationError(f"{config.connector_id} token exchange failed.")
    return payload


def encode_pkce_cookie(start: ConnectorOAuthStart) -> str:
    payload = {"cv": start.code_verifier or ""}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def decode_pkce_cookie(value: str | None) -> str | None:
    if not value:
        return None
    try:
        padding = "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(f"{value}{padding}")
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    verifier = payload.get("cv") if isinstance(payload, dict) else None
    return verifier if isinstance(verifier, str) and verifier else None


def _pkce_challenge(verifier: str) -> str:
    return pkce_challenge(verifier)


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _read_http_error(error: urllib.error.HTTPError) -> str:
    try:
        body = error.read().decode("utf-8")
        payload = json.loads(body)
        if isinstance(payload, dict):
            return str(payload.get("error_description") or payload.get("error") or "HTTP error")
    except Exception:
        pass
    return "HTTP error"
