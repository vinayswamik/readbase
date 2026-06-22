from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import GitlabConnectionResponse, GitlabProjectsResponse
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.connectors.oauth_core import oauth_states_match
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.gitlab_service import (
    GITLAB_OAUTH_STATE_TTL_SECONDS,
    build_gitlab_authorize_url,
    create_gitlab_oauth_state,
    disconnect_gitlab,
    exchange_gitlab_code_for_connection,
    get_gitlab_connection_status,
    list_visible_gitlab_projects,
)
from src.backend.application.services.workspace_service import user_can_access_workspace

router = APIRouter(tags=["gitlab"])
GITLAB_STATE_COOKIE_NAME = "readbase_gitlab_oauth_state"
logger = logging.getLogger(__name__)


@router.get("/me/integrations/gitlab/start")
def start_gitlab_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_gitlab_oauth_state()
    try:
        authorize_url = build_gitlab_authorize_url(state)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(GITLAB_STATE_COOKIE_NAME, state, max_age=GITLAB_OAUTH_STATE_TTL_SECONDS, httponly=True, samesite="lax", secure=SESSION_SECURE_COOKIE, path="/")
    return redirect


@router.get("/me/integrations/gitlab/callback")
def complete_gitlab_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    gitlab_state_cookie: str | None = Cookie(default=None, alias=GITLAB_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?gitlab_connected=1", status_code=303)
    redirect.delete_cookie(key=GITLAB_STATE_COOKIE_NAME, path="/")
    if not code or not oauth_states_match(state, gitlab_state_cookie):
        return RedirectResponse(url="/?gitlab_error=invalid_state", status_code=303)
    try:
        exchange_gitlab_code_for_connection(user.user_id, code)
    except ServiceError as exc:
        logger.warning("GitLab OAuth connection failed: %s", exc)
        return RedirectResponse(url="/?gitlab_error=connect_failed", status_code=303)
    return redirect


@router.get("/me/integrations/gitlab", response_model=GitlabConnectionResponse)
def gitlab_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_gitlab_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/gitlab", response_model=GitlabConnectionResponse)
def disconnect_gitlab_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return disconnect_gitlab(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/me/integrations/gitlab/projects", response_model=GitlabProjectsResponse)
def gitlab_projects(query: str = Query(default=""), user=Depends(require_authenticated_user)) -> dict:
    try:
        return {"projects": list_visible_gitlab_projects(user.user_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/gitlab/projects", response_model=GitlabProjectsResponse)
def workspace_gitlab_projects(workspace_id: str, query: str = Query(default=""), user=Depends(require_authenticated_user)) -> dict:
    if not user_can_access_workspace(user.user_id, user.email, workspace_id):
        from src.backend.application.services.exceptions import PermissionDeniedError

        raise service_error_to_http(PermissionDeniedError("Workspace access required."))
    try:
        return {"projects": list_visible_gitlab_projects(user.user_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
