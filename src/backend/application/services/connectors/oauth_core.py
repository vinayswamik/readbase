from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
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


def _app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/")


def oauth_states_match(provided: str | None, expected: str | None) -> bool:
    if provided is None or expected is None:
        return False
    return secrets.compare_digest(provided, expected)


def oauth_public_base_url(*, base_url_override_env: str | None = None) -> str:
    """Public origin for OAuth redirects; upgrades http->https when local SSL is configured."""
    if base_url_override_env:
        override = os.getenv(base_url_override_env, "").strip()
        if override:
            return override.rstrip("/")
    base = _app_base_url()
    if base.startswith("http://") and os.getenv("READBASE_SSL_CERTFILE", "").strip():
        return f"https://{base[len('http://'):]}"
    return base


def build_oauth_callback_url(
    callback_path: str,
    *,
    redirect_uri_env: str,
    base_url_override_env: str | None = None,
    require_https: bool = False,
    connector_label: str = "OAuth",
) -> str:
    configured = os.getenv(redirect_uri_env, "").strip()
    if configured:
        if require_https:
            require_https_redirect_uri(configured, connector_label=connector_label)
        require_redirect_uri_servable(configured, connector_label=connector_label)
        return configured
    url = f"{oauth_public_base_url(base_url_override_env=base_url_override_env)}{callback_path}"
    if require_https:
        require_https_redirect_uri(url, connector_label=connector_label)
    require_redirect_uri_servable(url, connector_label=connector_label)
    return url


def require_https_redirect_uri(url: str, *, connector_label: str = "OAuth") -> None:
    if not url.lower().startswith("https://"):
        raise ValidationError(
            f"{connector_label} requires an HTTPS redirect URI. Set the callback to an https URL "
            "(e.g. https://127.0.0.1:8000/... with local SSL, or an ngrok URL)."
        )


def require_redirect_uri_servable(url: str, *, connector_label: str = "Slack") -> None:
    """Reject local HTTPS callback URLs when Readbase is not configured to serve HTTPS."""
    if not url.lower().startswith("https://"):
        return
    if os.getenv("READBASE_SSL_CERTFILE", "").strip():
        return
    if _app_base_url().lower().startswith("https://"):
        return
    redirect_host = _redirect_uri_host(url)
    base_host = _redirect_uri_host(_app_base_url())
    if redirect_host and base_host and redirect_host != base_host and not _local_dev_host(redirect_host):
        return
    raise ValidationError(
        f"{connector_label} redirect URI uses HTTPS but Readbase is not configured for local SSL. "
        "Run scripts/setup_local_ssl.sh and set READBASE_SSL_* / APP_BASE_URL=https://..., "
        "or use an HTTP callback (http://127.0.0.1:8000/...) when serving over HTTP."
    )


def _redirect_uri_host(url: str) -> str | None:
    hostname = urllib.parse.urlparse(url).hostname
    return hostname.lower() if hostname else None


def _local_dev_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


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
