from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Response

from src.backend.application.services.auth.security_events import record_security_event
from src.backend.application.services.auth.sessions import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    refresh_user_session,
    resolve_session_user,
    revoke_user_session,
    set_session_cookie,
)
from src.backend.application.services.auth_service import AuthUser
from src.backend.application.services.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from src.backend.application.services.workspace_service import (
    get_workspace,
    get_owned_workspace,
)
from src.backend.infrastructure.storage.permissions import user_can_write_workspace_storage


def require_authenticated_user(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AuthUser:
    resolved = resolve_session_user(session_token)
    if resolved is None:
        clear_session_cookie(response)
        record_security_event("auth_session_invalid")
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")

    if resolved.should_rotate and session_token:
        rotated = refresh_user_session(session_token)
        if rotated:
            set_session_cookie(response, rotated[0], rotated[1])
            record_security_event("auth_session_rotated", user_id=resolved.user.user_id)
    return resolved.user


def require_workspace_access(
    workspace_id: str,
    user: AuthUser = Depends(require_authenticated_user),
):
    try:
        return get_workspace(
            user.user_id,
            workspace_id,
            user_email=user.email,
        )
    except (ResourceNotFoundError, ValidationError) as exc:
        record_security_event(
            "workspace_access_denied",
            user_id=user.user_id,
            workspace_id=workspace_id,
        )
        raise HTTPException(status_code=403, detail="Workspace access required.") from exc


def require_workspace_storage_write(
    workspace_id: str,
    user: AuthUser = Depends(require_authenticated_user),
):
    try:
        workspace = get_workspace(
            user.user_id,
            workspace_id,
            user_email=user.email,
        )
    except (ResourceNotFoundError, ValidationError) as exc:
        record_security_event(
            "workspace_write_denied",
            user_id=user.user_id,
            workspace_id=workspace_id,
        )
        raise HTTPException(status_code=403, detail="Workspace access required.") from exc

    if not user_can_write_workspace_storage(user.user_id, user.email, workspace_id):
        record_security_event(
            "workspace_connector_manager_denied",
            user_id=user.user_id,
            workspace_id=workspace_id,
        )
        raise HTTPException(
            status_code=403,
            detail="Workspace owner or connector manager access required.",
        )
    return workspace


def require_workspace_owner(
    workspace_id: str,
    user: AuthUser = Depends(require_authenticated_user),
):
    try:
        return get_owned_workspace(user.user_id, workspace_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found.") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail="Workspace owner access required.") from exc
