from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Response

from src.backend.application.services.auth_service import (
    ACCESS_TOKEN_TTL_SECONDS,
    REFRESH_TOKEN_TTL_SECONDS,
    SESSION_SECURE_COOKIE,
    AuthUser,
    create_access_token,
    create_refresh_token,
    parse_access_session,
    parse_refresh_session,
)
from src.backend.application.services.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from src.backend.application.services.workspace_service import (
    get_workspace,
    get_owned_workspace,
)

ACCESS_COOKIE_NAME = "readbase_access_token"
REFRESH_COOKIE_NAME = "readbase_refresh_token"


def require_authenticated_user(
    response: Response,
    access_token: str | None = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if access_token:
        access_session = parse_access_session(access_token)
        if access_session is not None:
            if access_session.should_refresh():
                set_access_cookie(response, access_session.user)
            return access_session.user

    if refresh_token:
        refresh_session = parse_refresh_session(refresh_token)
        if refresh_session is not None:
            set_access_cookie(response, refresh_session.user)
            return refresh_session.user

    clear_auth_cookies(response)
    raise HTTPException(status_code=401, detail="Session expired. Sign in again.")


def require_admin_user(user: AuthUser = Depends(require_authenticated_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def require_workspace_access(
    workspace_id: str,
    user: AuthUser = Depends(require_authenticated_user),
):
    try:
        return get_workspace(
            user.user_id,
            workspace_id,
            user_email=user.email,
            user_role=user.role,
        )
    except (ResourceNotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=403, detail="Workspace access required.") from exc


def require_workspace_owner(
    workspace_id: str,
    user: AuthUser = Depends(require_authenticated_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    try:
        return get_owned_workspace(user.user_id, workspace_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found.") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail="Workspace owner access required.") from exc


def set_access_cookie(response: Response, user: AuthUser) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=create_access_token(user),
        max_age=ACCESS_TOKEN_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )


def set_refresh_cookie(response: Response, user: AuthUser) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=create_refresh_token(user),
        max_age=REFRESH_TOKEN_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")
