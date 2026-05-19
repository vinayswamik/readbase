from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from secrets import token_urlsafe

import certifi
from sqlalchemy import select

from src.backend.config.settings import (
    BASE_DIR,
    READBASE_BOOTSTRAP_ADMIN_EMAILS,
    load_env_file,
)
from src.backend.application.services.exceptions import ValidationError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import AdminApproval, User, WorkspaceMember

load_env_file(BASE_DIR / ".env")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "").strip()

SESSION_SECRET = (
    os.getenv("APP_SESSION_SECRET")
    or os.getenv("READBASE_SESSION_SECRET")
    or "readbase-dev-session-secret"
)
ACCESS_TOKEN_TTL_SECONDS = int(
    os.getenv("APP_ACCESS_TOKEN_MAX_AGE_SECONDS")
    or "3600"
)
REFRESH_TOKEN_TTL_SECONDS = int(
    os.getenv("APP_REFRESH_TOKEN_MAX_AGE_SECONDS")
    or os.getenv("APP_SESSION_MAX_AGE_SECONDS")
    or os.getenv("READBASE_SESSION_TTL_SECONDS")
    or "2592000"
)
SESSION_SECURE_COOKIE = (os.getenv("APP_SESSION_COOKIE_SECURE", "false").strip().lower() == "true")
ACCESS_TOKEN_REFRESH_WINDOW_SECONDS = int(os.getenv("APP_ACCESS_TOKEN_REFRESH_WINDOW_SECONDS", "900"))

GOOGLE_CALLBACK_PATH = "/api/auth/google/callback"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
OAUTH_STATE_TTL_SECONDS = 600
logger = logging.getLogger(__name__)
TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    email: str
    name: str
    role: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
        }


@dataclass(frozen=True)
class GoogleIdentity:
    user_id: str
    email: str
    name: str


@dataclass(frozen=True)
class AuthSession:
    user: AuthUser
    expires_at: int

    def should_refresh(self) -> bool:
        remaining_seconds = self.expires_at - int(time.time())
        return remaining_seconds <= ACCESS_TOKEN_REFRESH_WINDOW_SECONDS


def create_google_oauth_state() -> str:
    return token_urlsafe(24)


def google_callback_url() -> str:
    if GOOGLE_REDIRECT_URI:
        return GOOGLE_REDIRECT_URI
    return f"{APP_BASE_URL.rstrip('/')}{GOOGLE_CALLBACK_PATH}"


def build_google_authorize_url(state: str) -> str:
    _validate_google_oauth_config()
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": google_callback_url(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_google_code_for_identity(code: str) -> GoogleIdentity:
    _validate_google_oauth_config()
    token_payload = _exchange_code_for_tokens(code)
    id_token = token_payload.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise ValidationError("Google login failed. Missing ID token.")

    claims = _verify_google_id_token(id_token)
    return GoogleIdentity(
        user_id=_required_str(claims, "sub"),
        email=_required_str(claims, "email"),
        name=claims.get("name") if isinstance(claims.get("name"), str) else "Google User",
    )


def exchange_google_code_for_user(code: str) -> AuthUser:
    identity = exchange_google_code_for_identity(code)
    return upsert_authenticated_user(identity, role="member")


def upsert_authenticated_user(identity: GoogleIdentity, role: str) -> AuthUser:
    normalized_role = normalize_login_role(role)
    email_key = normalize_email_key(identity.email)
    with session_scope() as session:
        user = session.get(User, identity.user_id)
        existing_for_email = session.scalar(select(User).where(User.email_key == email_key))
        if user is None and existing_for_email is not None:
            user = existing_for_email
            user.user_id = identity.user_id
        if user is None:
            user = User(
                user_id=identity.user_id,
                email=identity.email,
                email_key=email_key,
                name=identity.name,
            )
            session.add(user)
        else:
            user.email = identity.email
            user.email_key = email_key
            user.name = identity.name

        for membership in session.scalars(
            select(WorkspaceMember).where(WorkspaceMember.member_email_key == email_key)
        ):
            membership.user_id = identity.user_id

    return AuthUser(
        user_id=identity.user_id,
        email=identity.email,
        name=identity.name,
        role=normalized_role,
    )


def is_admin_approved(email: str) -> bool:
    email_key = normalize_email_key(email)
    with session_scope() as session:
        approval = session.scalar(
            select(AdminApproval).where(
                AdminApproval.email_key == email_key,
                AdminApproval.active.is_(True),
            )
        )
        return approval is not None


def seed_bootstrap_admins() -> None:
    emails = [
        item.strip()
        for item in READBASE_BOOTSTRAP_ADMIN_EMAILS.replace(";", ",").split(",")
        if item.strip()
    ]
    if not emails:
        return

    with session_scope() as session:
        for email in emails:
            email_key = normalize_email_key(email)
            approval = session.scalar(
                select(AdminApproval).where(AdminApproval.email_key == email_key)
            )
            if approval is None:
                session.add(AdminApproval(email=email.strip(), email_key=email_key, active=True))
            else:
                approval.email = email.strip()
                approval.active = True


def normalize_login_role(role: str) -> str:
    normalized_role = role.strip().lower()
    if normalized_role not in {"admin", "member"}:
        raise ValidationError("Login role is invalid.")
    return normalized_role


def normalize_login_portal(portal: str) -> str:
    normalized_portal = portal.strip().lower()
    if normalized_portal not in {"admin", "member"}:
        raise ValidationError("Login portal is invalid.")
    return normalized_portal


def normalize_email_key(email: str) -> str:
    normalized = email.strip().casefold()
    if not normalized or "@" not in normalized:
        raise ValidationError("Email address is required.")
    if len(normalized) > 320:
        raise ValidationError("Email address is too long.")
    return normalized


def create_access_token(user: AuthUser) -> str:
    return _create_signed_token(user=user, ttl_seconds=ACCESS_TOKEN_TTL_SECONDS, token_type="access")


def create_refresh_token(user: AuthUser) -> str:
    return _create_signed_token(user=user, ttl_seconds=REFRESH_TOKEN_TTL_SECONDS, token_type="refresh")


def _create_signed_token(user: AuthUser, ttl_seconds: int, token_type: str) -> str:
    issued_at = int(time.time())
    payload = {
        "typ": token_type,
        "sub": user.user_id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_part = _b64url_encode(payload_bytes)
    signature_part = _sign_payload(payload_part)
    return f"{payload_part}.{signature_part}"


def parse_access_session(token: str) -> AuthSession | None:
    return _parse_session(token=token, expected_type="access")


def parse_refresh_session(token: str) -> AuthSession | None:
    return _parse_session(token=token, expected_type="refresh")


def _parse_session(token: str, expected_type: str) -> AuthSession | None:
    if "." not in token:
        return None
    payload_part, signature_part = token.split(".", 1)
    expected_signature = _sign_payload(payload_part)
    if not hmac.compare_digest(signature_part, expected_signature):
        return None

    try:
        payload_raw = _b64url_decode(payload_part)
        payload = json.loads(payload_raw)
    except (ValueError, json.JSONDecodeError):
        return None

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at <= int(time.time()):
        return None
    token_type = payload.get("typ")
    if token_type != expected_type:
        return None

    user_id = payload.get("sub")
    email = payload.get("email")
    name = payload.get("name")
    role = payload.get("role", "member")
    if not isinstance(user_id, str) or not isinstance(email, str) or not isinstance(name, str):
        return None
    if not isinstance(role, str) or role not in {"admin", "member"}:
        return None

    return AuthSession(
        user=AuthUser(user_id=user_id, email=email, name=name, role=role),
        expires_at=expires_at,
    )


def _sign_payload(payload_part: str) -> str:
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload_part.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(signature)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _validate_google_oauth_config() -> None:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise ValidationError("Google OAuth is not configured. Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")


def _exchange_code_for_tokens(code: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": google_callback_url(),
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GOOGLE_TOKEN_ENDPOINT,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10, context=TLS_CONTEXT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = _read_http_error_json(exc)
        description = (
            error_body.get("error_description")
            if isinstance(error_body, dict)
            else None
        )
        detail = description or "Google token endpoint returned HTTP error."
        raise ValidationError(f"Google login failed while exchanging auth code: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValidationError(f"Unable to reach Google OAuth servers: {_error_reason(exc)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError("Received invalid token response from Google.") from exc
    if isinstance(payload, dict) and payload.get("error"):
        raise ValidationError("Google login failed while exchanging auth code.")
    if not isinstance(payload, dict):
        raise ValidationError("Unexpected token response from Google.")
    return payload


def _verify_google_id_token(id_token: str) -> dict:
    url = f"{GOOGLE_TOKENINFO_ENDPOINT}?{urllib.parse.urlencode({'id_token': id_token})}"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10, context=TLS_CONTEXT) as response:
            claims = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("Google tokeninfo verification failed with HTTP error: %s", exc)
        claims = _decode_jwt_payload_unverified(id_token)
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("Google tokeninfo verification failed with network error: %s", exc)
        claims = _decode_jwt_payload_unverified(id_token)
    except json.JSONDecodeError as exc:
        logger.warning("Google tokeninfo verification failed with JSON error: %s", exc)
        claims = _decode_jwt_payload_unverified(id_token)
    if not isinstance(claims, dict):
        raise ValidationError("Invalid Google token verification payload.")

    aud = claims.get("aud")
    iss = claims.get("iss")
    exp_raw = claims.get("exp")
    email_verified = claims.get("email_verified")
    if aud != GOOGLE_CLIENT_ID:
        raise ValidationError("Google login token audience mismatch.")
    if iss not in GOOGLE_ISSUERS:
        raise ValidationError("Google login token issuer mismatch.")
    try:
        exp = int(exp_raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Google login token expiry is invalid.") from exc
    if exp <= int(time.time()):
        raise ValidationError("Google login token has expired.")
    if str(email_verified).lower() != "true":
        raise ValidationError("Google account email is not verified.")

    return claims


def _required_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Google login response missing '{key}'.")
    return value


def _read_http_error_json(error: urllib.error.HTTPError) -> dict | None:
    try:
        body = error.read().decode("utf-8")
        payload = json.loads(body)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _decode_jwt_payload_unverified(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValidationError("Google ID token format is invalid.")
    payload_part = parts[1]
    try:
        raw_payload = _b64url_decode(payload_part).decode("utf-8")
        payload = json.loads(raw_payload)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error) as exc:
        raise ValidationError("Unable to decode Google ID token payload.") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Decoded Google ID token payload is invalid.")
    return payload


def _error_reason(error: urllib.error.URLError | TimeoutError) -> str:
    if isinstance(error, TimeoutError):
        return "request timed out"
    reason = getattr(error, "reason", None)
    return str(reason) if reason else "unknown network error"
