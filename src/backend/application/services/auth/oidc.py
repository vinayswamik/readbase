from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from secrets import token_urlsafe

import certifi
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

from src.backend.application.services.exceptions import ValidationError
from src.backend.config.settings import BASE_DIR, load_env_file

load_env_file(BASE_DIR / ".env")

logger = logging.getLogger(__name__)
TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
OAUTH_STATE_TTL_SECONDS = 600
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").strip()
OIDC_CALLBACK_PATH = "/api/auth/callback"


@dataclass(frozen=True)
class OidcConfig:
    provider_name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    jwks_url: str
    issuer: str
    redirect_uri: str
    scopes: str
    audience: str | None = None


@dataclass(frozen=True)
class OidcIdentity:
    user_id: str
    email: str
    name: str


@dataclass(frozen=True)
class OidcStartContext:
    state: str
    nonce: str
    code_verifier: str


def load_oidc_config() -> OidcConfig:
    client_id = os.getenv("READBASE_OIDC_CLIENT_ID", "").strip() or os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("READBASE_OIDC_CLIENT_SECRET", "").strip() or os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    issuer = os.getenv("READBASE_OIDC_ISSUER", "").strip() or "https://accounts.google.com"
    provider_name = os.getenv("READBASE_OIDC_PROVIDER_NAME", "").strip() or "your organization"
    scopes = os.getenv("READBASE_OIDC_SCOPES", "").strip() or "openid email profile"
    redirect_uri = (
        os.getenv("READBASE_OIDC_REDIRECT_URI", "").strip()
        or os.getenv("GOOGLE_REDIRECT_URI", "").strip()
        or f"{APP_BASE_URL.rstrip('/')}{OIDC_CALLBACK_PATH}"
    )
    authorize_url = os.getenv("READBASE_OIDC_AUTHORIZE_URL", "").strip()
    token_url = os.getenv("READBASE_OIDC_TOKEN_URL", "").strip()
    jwks_url = os.getenv("READBASE_OIDC_JWKS_URL", "").strip()
    audience = os.getenv("READBASE_OIDC_AUDIENCE", "").strip() or None

    if not authorize_url:
        if issuer.rstrip("/").endswith("accounts.google.com"):
            authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
        else:
            authorize_url = f"{issuer.rstrip('/')}/authorize"
    if not token_url:
        if issuer.rstrip("/").endswith("accounts.google.com"):
            token_url = "https://oauth2.googleapis.com/token"
        else:
            token_url = f"{issuer.rstrip('/')}/token"
    if not jwks_url:
        if issuer.rstrip("/").endswith("accounts.google.com"):
            jwks_url = "https://www.googleapis.com/oauth2/v3/certs"
        else:
            jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"

    if not client_id or not client_secret:
        raise ValidationError("OIDC login is not configured. Set READBASE_OIDC_CLIENT_ID and READBASE_OIDC_CLIENT_SECRET.")

    return OidcConfig(
        provider_name=provider_name,
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=authorize_url,
        token_url=token_url,
        jwks_url=jwks_url,
        issuer=issuer,
        redirect_uri=redirect_uri,
        scopes=scopes,
        audience=audience,
    )


def create_oidc_start_context() -> OidcStartContext:
    code_verifier = token_urlsafe(48)
    return OidcStartContext(
        state=token_urlsafe(24),
        nonce=token_urlsafe(24),
        code_verifier=code_verifier,
    )


def build_oidc_authorize_url(config: OidcConfig, context: OidcStartContext) -> str:
    challenge = _pkce_challenge(context.code_verifier)
    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": config.scopes,
        "state": context.state,
        "nonce": context.nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{config.authorize_url}?{urllib.parse.urlencode(params)}"


def exchange_oidc_code(code: str, code_verifier: str, nonce: str) -> OidcIdentity:
    from src.backend.application.services.auth.oauth_codes import consume_oauth_code

    if not consume_oauth_code(code):
        raise ValidationError("OIDC login failed. Authorization code already used.")
    config = load_oidc_config()
    token_payload = _exchange_code_for_tokens(config, code, code_verifier)
    id_token = token_payload.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise ValidationError("OIDC login failed. Missing ID token.")
    claims = _verify_id_token(config, id_token, nonce)
    return OidcIdentity(
        user_id=_required_str(claims, "sub"),
        email=_required_str(claims, "email"),
        name=claims.get("name") if isinstance(claims.get("name"), str) else config.provider_name,
    )


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _exchange_code_for_tokens(config: OidcConfig, code: str, code_verifier: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        config.token_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10, context=TLS_CONTEXT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = _read_http_error_json(exc)
        description = error_body.get("error_description") if isinstance(error_body, dict) else None
        detail = description or "OIDC token endpoint returned HTTP error."
        raise ValidationError(f"OIDC login failed while exchanging auth code: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValidationError(f"Unable to reach OIDC provider: {_error_reason(exc)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError("Received invalid token response from OIDC provider.") from exc
    if isinstance(payload, dict) and payload.get("error"):
        raise ValidationError("OIDC login failed while exchanging auth code.")
    if not isinstance(payload, dict):
        raise ValidationError("Unexpected token response from OIDC provider.")
    return payload


def _verify_id_token(config: OidcConfig, id_token: str, expected_nonce: str) -> dict:
    try:
        jwk_client = _jwks_client(config.jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)
    except PyJWKClientConnectionError as exc:
        raise ValidationError("Unable to verify OIDC login token. JWKS fetch failed.") from exc
    audience = config.audience or config.client_id
    decode_options = {"require": ["exp", "sub", "email"]}
    try:
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=audience,
            issuer=config.issuer,
            options=decode_options,
            leeway=60,
        )
    except jwt.PyJWTError as exc:
        if config.issuer.rstrip("/").endswith("accounts.google.com"):
            try:
                claims = jwt.decode(
                    id_token,
                    signing_key.key,
                    algorithms=["RS256", "ES256"],
                    audience=audience,
                    issuer="accounts.google.com",
                    options=decode_options,
                    leeway=60,
                )
            except jwt.PyJWTError as inner_exc:
                raise ValidationError("OIDC ID token signature verification failed.") from inner_exc
        else:
            raise ValidationError("OIDC ID token signature verification failed.") from exc

    authorized_party = claims.get("azp")
    if isinstance(authorized_party, str) and authorized_party and authorized_party != config.client_id:
        raise ValidationError("OIDC ID token authorized party mismatch.")

    nonce = claims.get("nonce")
    if not isinstance(nonce, str) or nonce != expected_nonce:
        raise ValidationError("OIDC ID token nonce mismatch.")
    email_verified = claims.get("email_verified")
    if email_verified is False:
        raise ValidationError("OIDC account email is not verified.")
    return claims


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600, ssl_context=TLS_CONTEXT)


def _required_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"OIDC login response missing '{key}'.")
    return value


def _read_http_error_json(error: urllib.error.HTTPError) -> dict | None:
    try:
        body = error.read().decode("utf-8")
        payload = json.loads(body)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _error_reason(error: urllib.error.URLError | TimeoutError) -> str:
    if isinstance(error, TimeoutError):
        return "request timed out"
    reason = getattr(error, "reason", None)
    return str(reason) if reason else "unknown network error"
