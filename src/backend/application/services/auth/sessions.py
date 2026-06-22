from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from src.backend.application.services.auth.config import session_cookie_secure
from src.backend.application.services.auth.types import AuthUser, normalize_email_key
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import User, UserSession, WorkspaceMember

SESSION_COOKIE_NAME = "readbase_session"
SESSION_TTL_SECONDS = int(
    os.getenv("APP_REFRESH_TOKEN_MAX_AGE_SECONDS")
    or os.getenv("APP_SESSION_MAX_AGE_SECONDS")
    or os.getenv("READBASE_SESSION_TTL_SECONDS")
    or "604800"
)
SESSION_IDLE_TIMEOUT_SECONDS = int(os.getenv("APP_SESSION_IDLE_TIMEOUT_SECONDS", "86400"))
SESSION_REFRESH_WINDOW_SECONDS = int(os.getenv("APP_ACCESS_TOKEN_REFRESH_WINDOW_SECONDS", "900"))


@dataclass(frozen=True)
class ResolvedSession:
    user: AuthUser
    session_token: str
    expires_at: datetime
    should_rotate: bool


def create_user_session(user: AuthUser) -> tuple[str, datetime]:
    session_token = _generate_session_token()
    expires_at = _utc_now() + timedelta(seconds=SESSION_TTL_SECONDS)
    with session_scope() as session:
        session.add(
            UserSession(
                session_id=_session_id(),
                session_token_hash=_hash_token(session_token),
                user_id=user.user_id,
                expires_at=expires_at,
            )
        )
    return session_token, expires_at


def resolve_session_user(session_token: str | None) -> ResolvedSession | None:
    if not session_token:
        return None
    token_hash = _hash_token(session_token)
    with session_scope() as session:
        record = session.scalar(
            select(UserSession).where(
                UserSession.session_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
        if record is None:
            return None
        if _as_utc(record.expires_at) <= _utc_now():
            record.revoked_at = _utc_now()
            return None
        if record.last_used_at is not None:
            idle_seconds = int((_utc_now() - _as_utc(record.last_used_at)).total_seconds())
            if idle_seconds > SESSION_IDLE_TIMEOUT_SECONDS:
                record.revoked_at = _utc_now()
                return None
        user = session.get(User, record.user_id)
        if user is None:
            record.revoked_at = _utc_now()
            return None
        record.last_used_at = _utc_now()
        remaining = int((_as_utc(record.expires_at) - _utc_now()).total_seconds())
        should_rotate = remaining <= SESSION_REFRESH_WINDOW_SECONDS
        return ResolvedSession(
            user=AuthUser(user_id=user.user_id, email=user.email, name=user.name),
            session_token=session_token,
            expires_at=record.expires_at,
            should_rotate=should_rotate,
        )


def refresh_user_session(session_token: str) -> tuple[str, datetime] | None:
    resolved = resolve_session_user(session_token)
    if resolved is None or not resolved.should_rotate:
        return None
    token_hash = _hash_token(session_token)
    new_token = _generate_session_token()
    new_expires = _utc_now() + timedelta(seconds=SESSION_TTL_SECONDS)
    with session_scope() as session:
        record = session.scalar(
            select(UserSession).where(UserSession.session_token_hash == token_hash)
        )
        if record is None or record.revoked_at is not None:
            return None
        record.revoked_at = _utc_now()
        session.add(
            UserSession(
                session_id=_session_id(),
                session_token_hash=_hash_token(new_token),
                user_id=record.user_id,
                expires_at=new_expires,
                rotated_from_session_id=record.session_id,
            )
        )
    return new_token, new_expires


def revoke_user_session(session_token: str | None) -> None:
    if not session_token:
        return
    token_hash = _hash_token(session_token)
    with session_scope() as session:
        record = session.scalar(
            select(UserSession).where(UserSession.session_token_hash == token_hash)
        )
        if record is not None and record.revoked_at is None:
            record.revoked_at = _utc_now()


def upsert_oidc_user(identity) -> AuthUser:
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

    from src.backend.application.services.workspace_invite_service import sync_pending_invites_for_user

    sync_pending_invites_for_user(identity.user_id, identity.email)
    return AuthUser(user_id=identity.user_id, email=identity.email, name=identity.name)


def set_session_cookie(response, session_token: str, expires_at: datetime) -> None:
    max_age = max(0, int((expires_at - _utc_now()).total_seconds()))
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=session_cookie_secure(),
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def _generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def _session_id() -> str:
    return secrets.token_urlsafe(16)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
