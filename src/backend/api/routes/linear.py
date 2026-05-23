from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import AddWorkspaceLinearSourceRequest, LinearConnectionResponse, LinearSelectableSourcesResponse, WorkspaceLinearSourceResponse, WorkspaceLinearSourcesResponse
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.linear_service import (
    LINEAR_OAUTH_STATE_TTL_SECONDS,
    add_workspace_linear_source,
    build_linear_authorize_url,
    create_linear_oauth_state,
    disconnect_linear,
    exchange_linear_code_for_connection,
    get_linear_connection_status,
    list_visible_linear_sources,
    list_workspace_linear_sources,
    remove_workspace_linear_source,
    sync_workspace_linear_source,
)

router = APIRouter(tags=["linear"])
LINEAR_STATE_COOKIE_NAME = "readbase_linear_oauth_state"


@router.get("/me/integrations/linear/start")
def start_linear_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_linear_oauth_state()
    try:
        authorize_url = build_linear_authorize_url(state)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(LINEAR_STATE_COOKIE_NAME, state, max_age=LINEAR_OAUTH_STATE_TTL_SECONDS, httponly=True, samesite="lax", secure=SESSION_SECURE_COOKIE, path="/")
    return redirect


@router.get("/me/integrations/linear/callback")
def complete_linear_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    linear_state_cookie: str | None = Cookie(default=None, alias=LINEAR_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?linear_connected=1", status_code=303)
    redirect.delete_cookie(key=LINEAR_STATE_COOKIE_NAME, path="/")
    if not code or not state or not linear_state_cookie or state != linear_state_cookie:
        return RedirectResponse(url="/?linear_error=invalid_state", status_code=303)
    try:
        exchange_linear_code_for_connection(user.user_id, code)
    except ServiceError:
        return RedirectResponse(url="/?linear_error=connect_failed", status_code=303)
    return redirect


@router.get("/me/integrations/linear", response_model=LinearConnectionResponse)
def linear_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_linear_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/linear", response_model=LinearConnectionResponse)
def disconnect_linear_connection(
    remove_data: bool = Query(default=False),
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return disconnect_linear(user.user_id, remove_data=remove_data)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/me/integrations/linear/sources", response_model=LinearSelectableSourcesResponse)
def linear_selectable_sources(query: str = Query(default=""), user=Depends(require_authenticated_user)) -> dict:
    try:
        return {"sources": list_visible_linear_sources(user.user_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/linear/sources", response_model=WorkspaceLinearSourcesResponse)
def workspace_linear_sources(workspace_id: str, user=Depends(require_authenticated_user)) -> dict:
    try:
        return {"sources": list_workspace_linear_sources(workspace_id, user.user_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/linear/sources", response_model=WorkspaceLinearSourceResponse)
def add_linear_source(workspace_id: str, payload: AddWorkspaceLinearSourceRequest, user=Depends(require_authenticated_user)) -> dict:
    try:
        return add_workspace_linear_source(workspace_id, user.user_id, user.email, payload.dict())
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/workspaces/{workspace_id}/linear/sources/{source_id}", response_model=WorkspaceLinearSourceResponse)
def remove_linear_source(workspace_id: str, source_id: str, user=Depends(require_authenticated_user)) -> dict:
    try:
        return remove_workspace_linear_source(workspace_id, source_id, user.user_id, user.email)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/linear/sources/{source_id}/sync", response_model=WorkspaceLinearSourceResponse)
def sync_linear_source(workspace_id: str, source_id: str, user=Depends(require_authenticated_user)) -> dict:
    try:
        return sync_workspace_linear_source(source_id, workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
