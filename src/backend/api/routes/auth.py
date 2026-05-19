from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Query, Response
from fastapi.responses import RedirectResponse

from src.backend.api.auth import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    set_access_cookie,
    set_refresh_cookie,
)
from src.backend.api.schemas import SessionResponse
from src.backend.application.services.exceptions import ValidationError
from src.backend.application.services.auth_service import (
    OAUTH_STATE_TTL_SECONDS,
    SESSION_SECURE_COOKIE,
    build_google_authorize_url,
    create_google_oauth_state,
    exchange_google_code_for_identity,
    is_admin_approved,
    normalize_login_portal,
    parse_access_session,
    parse_refresh_session,
    upsert_authenticated_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])
OAUTH_STATE_COOKIE_NAME = "readbase_oauth_state"
OAUTH_PORTAL_COOKIE_NAME = "readbase_oauth_portal"
logger = logging.getLogger(__name__)


@router.get("/google/start")
def start_google_login(portal: str = Query(default="member")) -> RedirectResponse:
    try:
        normalized_portal = normalize_login_portal(portal)
    except ValidationError:
        normalized_portal = "member"

    state = create_google_oauth_state()
    redirect = RedirectResponse(url=build_google_authorize_url(state), status_code=302)
    redirect.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    redirect.set_cookie(
        key=OAUTH_PORTAL_COOKIE_NAME,
        value=normalized_portal,
        max_age=OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    return redirect


@router.get("/google/callback")
def complete_google_login(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    oauth_state_cookie: str | None = Cookie(default=None, alias=OAUTH_STATE_COOKIE_NAME),
    oauth_portal_cookie: str | None = Cookie(default=None, alias=OAUTH_PORTAL_COOKIE_NAME),
) -> RedirectResponse:
    if not code or not state or not oauth_state_cookie or state != oauth_state_cookie:
        return _redirect_with_auth_error("invalid_state")

    try:
        portal = normalize_login_portal(oauth_portal_cookie or "member")
        identity = exchange_google_code_for_identity(code)
        if portal == "admin" and not is_admin_approved(identity.email):
            return _redirect_with_auth_error("admin_not_approved")
        user = upsert_authenticated_user(identity, role=portal)
    except ValidationError as exc:
        logger.warning("Google login callback failed: %s", exc)
        return _redirect_with_auth_error("google_auth_failed")

    redirect = RedirectResponse(url="/", status_code=303)
    set_access_cookie(redirect, user)
    set_refresh_cookie(redirect, user)
    redirect.delete_cookie(key=OAUTH_STATE_COOKIE_NAME, path="/")
    redirect.delete_cookie(key=OAUTH_PORTAL_COOKIE_NAME, path="/")
    return redirect


@router.get("/session", response_model=SessionResponse)
def current_session(
    response: Response,
    access_token: str | None = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> dict:
    if access_token:
        access_session = parse_access_session(access_token)
        if access_session is not None:
            if access_session.should_refresh():
                set_access_cookie(response, access_session.user)
            return {"authenticated": True, "user": access_session.user.to_dict()}

    if refresh_token:
        refresh_session = parse_refresh_session(refresh_token)
        if refresh_session is not None:
            set_access_cookie(response, refresh_session.user)
            return {"authenticated": True, "user": refresh_session.user.to_dict()}

    clear_auth_cookies(response)
    return {"authenticated": False, "user": None}


@router.post("/logout", response_model=SessionResponse)
def logout(response: Response) -> dict:
    clear_auth_cookies(response)
    response.delete_cookie(key=OAUTH_STATE_COOKIE_NAME, path="/")
    response.delete_cookie(key=OAUTH_PORTAL_COOKIE_NAME, path="/")
    return {"authenticated": False, "user": None}


def _redirect_with_auth_error(error_code: str) -> RedirectResponse:
    redirect = RedirectResponse(url=f"/?auth_error={error_code}", status_code=303)
    clear_auth_cookies(redirect)
    redirect.delete_cookie(key=OAUTH_STATE_COOKIE_NAME, path="/")
    redirect.delete_cookie(key=OAUTH_PORTAL_COOKIE_NAME, path="/")
    return redirect
