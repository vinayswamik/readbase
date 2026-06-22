from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Query, Request, Response
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user
from src.backend.api.schemas import SessionResponse
from src.backend.application.services.auth.config import session_cookie_secure
from src.backend.application.services.auth.oidc import (
    OAUTH_STATE_TTL_SECONDS,
    build_oidc_authorize_url,
    create_oidc_start_context,
    exchange_oidc_code,
    load_oidc_config,
)
from src.backend.application.services.auth.csrf import (
    CSRF_COOKIE_NAME,
    clear_csrf_cookie,
    generate_csrf_token,
    set_csrf_cookie,
)
from src.backend.application.services.auth.lockout import (
    is_auth_locked,
    record_auth_failure,
    record_auth_success,
)
from src.backend.application.services.auth.security_events import record_security_event
from src.backend.application.services.connectors.oauth_core import oauth_states_match
from src.backend.application.services.auth.sessions import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    create_user_session,
    revoke_user_session,
    set_session_cookie,
    upsert_oidc_user,
)
from src.backend.application.services.exceptions import ValidationError

router = APIRouter(prefix="/auth", tags=["auth"])
OAUTH_STATE_COOKIE_NAME = "readbase_oauth_state"
OIDC_PKCE_COOKIE_NAME = "readbase_oidc_pkce"
OIDC_NONCE_COOKIE_NAME = "readbase_oidc_nonce"
logger = logging.getLogger(__name__)


@router.get("/start")
def start_oidc_login() -> RedirectResponse:
    config = load_oidc_config()
    context = create_oidc_start_context()
    redirect = RedirectResponse(url=build_oidc_authorize_url(config, context), status_code=302)
    _set_oauth_cookies(redirect, context.state, context.code_verifier, context.nonce)
    record_security_event("auth_login_started", provider=config.provider_name)
    return redirect


@router.get("/google/start")
def start_google_login_alias() -> RedirectResponse:
    return start_oidc_login()


@router.get("/callback")
def complete_oidc_login(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    oauth_state_cookie: str | None = Cookie(default=None, alias=OAUTH_STATE_COOKIE_NAME),
    oidc_pkce_cookie: str | None = Cookie(default=None, alias=OIDC_PKCE_COOKIE_NAME),
    oidc_nonce_cookie: str | None = Cookie(default=None, alias=OIDC_NONCE_COOKIE_NAME),
) -> RedirectResponse:
    client_ip = request.client.host if request.client else "unknown"
    locked, _retry_after = is_auth_locked(client_ip)
    if locked:
        record_security_event("auth_login_failed", reason="lockout", client_ip=client_ip)
        return _redirect_with_auth_error("too_many_attempts")

    if (
        not code
        or not oauth_states_match(state, oauth_state_cookie)
        or not oidc_pkce_cookie
        or not oidc_nonce_cookie
    ):
        record_auth_failure(client_ip)
        record_security_event("auth_login_failed", reason="invalid_state", client_ip=client_ip)
        return _redirect_with_auth_error("invalid_state")

    try:
        identity = exchange_oidc_code(code, oidc_pkce_cookie, oidc_nonce_cookie)
        user = upsert_oidc_user(identity)
        session_token, expires_at = create_user_session(user)
        csrf_token = generate_csrf_token()
    except ValidationError as exc:
        record_auth_failure(client_ip)
        logger.warning("OIDC login callback failed: %s", exc)
        record_security_event("auth_login_failed", reason="oidc_exchange_failed", client_ip=client_ip)
        return _redirect_with_auth_error("oidc_auth_failed")

    record_auth_success(client_ip)

    redirect = RedirectResponse(url="/", status_code=303)
    set_session_cookie(redirect, session_token, expires_at)
    set_csrf_cookie(redirect, csrf_token)
    _clear_oauth_cookies(redirect)
    record_security_event("auth_login_success", user_id=user.user_id)
    return redirect


@router.get("/google/callback")
def complete_google_login_alias(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    oauth_state_cookie: str | None = Cookie(default=None, alias=OAUTH_STATE_COOKIE_NAME),
    oidc_pkce_cookie: str | None = Cookie(default=None, alias=OIDC_PKCE_COOKIE_NAME),
    oidc_nonce_cookie: str | None = Cookie(default=None, alias=OIDC_NONCE_COOKIE_NAME),
) -> RedirectResponse:
    return complete_oidc_login(
        request,
        code,
        state,
        oauth_state_cookie,
        oidc_pkce_cookie,
        oidc_nonce_cookie,
    )


@router.get("/session", response_model=SessionResponse)
def current_session(
    request: Request,
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict:
    from src.backend.application.services.auth.sessions import refresh_user_session, resolve_session_user

    resolved = resolve_session_user(session_token)
    if resolved is None:
        clear_session_cookie(response)
        clear_csrf_cookie(response)
        return {"authenticated": False, "user": None}

    if resolved.should_rotate and session_token:
        rotated = refresh_user_session(session_token)
        if rotated:
            set_session_cookie(response, rotated[0], rotated[1])
    if not request.cookies.get(CSRF_COOKIE_NAME):
        set_csrf_cookie(response, generate_csrf_token())
    return {"authenticated": True, "user": resolved.user.to_dict()}


@router.post("/logout", response_model=SessionResponse)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict:
    revoke_user_session(session_token)
    clear_session_cookie(response)
    clear_csrf_cookie(response)
    _clear_oauth_cookies(response)
    record_security_event("auth_logout")
    return {"authenticated": False, "user": None}


def _set_oauth_cookies(redirect: RedirectResponse, state: str, code_verifier: str, nonce: str) -> None:
    secure = session_cookie_secure()
    redirect.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    redirect.set_cookie(
        key=OIDC_PKCE_COOKIE_NAME,
        value=code_verifier,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    redirect.set_cookie(
        key=OIDC_NONCE_COOKIE_NAME,
        value=nonce,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def _clear_oauth_cookies(response: Response) -> None:
    response.delete_cookie(key=OAUTH_STATE_COOKIE_NAME, path="/")
    response.delete_cookie(key=OIDC_PKCE_COOKIE_NAME, path="/")
    response.delete_cookie(key=OIDC_NONCE_COOKIE_NAME, path="/")


def _redirect_with_auth_error(error_code: str) -> RedirectResponse:
    redirect = RedirectResponse(url=f"/?auth_error={error_code}", status_code=303)
    clear_session_cookie(redirect)
    clear_csrf_cookie(redirect)
    _clear_oauth_cookies(redirect)
    return redirect
