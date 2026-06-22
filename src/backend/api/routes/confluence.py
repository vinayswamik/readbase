from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user, require_workspace_access, require_workspace_storage_write
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import AddWorkspaceConfluenceSpaceRequest, ConfluenceConnectionResponse, ConfluenceSpacesResponse, WorkspaceConfluenceSourceResponse, WorkspaceConfluenceSourcesResponse
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.connectors.oauth_core import oauth_states_match
from src.backend.application.services.confluence_service import (
    CONFLUENCE_OAUTH_STATE_TTL_SECONDS,
    add_workspace_confluence_source,
    build_confluence_authorize_url,
    create_confluence_oauth_state,
    disconnect_confluence,
    exchange_confluence_code_for_connection,
    get_confluence_connection_status,
    list_visible_confluence_spaces,
    list_workspace_confluence_sources,
    remove_workspace_confluence_source,
    sync_workspace_confluence_source,
)
from src.backend.application.services.exceptions import ServiceError

router = APIRouter(tags=["confluence"])
CONFLUENCE_STATE_COOKIE_NAME = "readbase_confluence_oauth_state"


@router.get("/me/integrations/confluence/start")
def start_confluence_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_confluence_oauth_state()
    try:
        authorize_url = build_confluence_authorize_url(state)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(CONFLUENCE_STATE_COOKIE_NAME, state, max_age=CONFLUENCE_OAUTH_STATE_TTL_SECONDS, httponly=True, samesite="lax", secure=SESSION_SECURE_COOKIE, path="/")
    return redirect


@router.get("/me/integrations/confluence/callback")
def complete_confluence_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    confluence_state_cookie: str | None = Cookie(default=None, alias=CONFLUENCE_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?confluence_connected=1", status_code=303)
    redirect.delete_cookie(key=CONFLUENCE_STATE_COOKIE_NAME, path="/")
    if not code or not oauth_states_match(state, confluence_state_cookie):
        return RedirectResponse(url="/?confluence_error=invalid_state", status_code=303)
    try:
        exchange_confluence_code_for_connection(user.user_id, code)
    except ServiceError:
        return RedirectResponse(url="/?confluence_error=connect_failed", status_code=303)
    return redirect


@router.get("/me/integrations/confluence", response_model=ConfluenceConnectionResponse)
def confluence_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_confluence_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/confluence", response_model=ConfluenceConnectionResponse)
def disconnect_confluence_connection(
    remove_data: bool = Query(default=False),
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return disconnect_confluence(user.user_id, remove_data=remove_data)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/me/integrations/confluence/spaces", response_model=ConfluenceSpacesResponse)
def confluence_spaces(query: str = Query(default=""), user=Depends(require_authenticated_user)) -> dict:
    try:
        return {"spaces": list_visible_confluence_spaces(user.user_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/confluence/sources", response_model=WorkspaceConfluenceSourcesResponse)
def workspace_confluence_sources(
    workspace_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return {"sources": list_workspace_confluence_sources(workspace_id, user.user_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/confluence/sources", response_model=WorkspaceConfluenceSourceResponse)
def add_confluence_source(
    workspace_id: str,
    payload: AddWorkspaceConfluenceSpaceRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_storage_write),
) -> dict:
    try:
        return add_workspace_confluence_source(workspace_id, user.user_id, user.email, payload.dict())
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/workspaces/{workspace_id}/confluence/sources/{source_id}", response_model=WorkspaceConfluenceSourceResponse)
def remove_confluence_source(
    workspace_id: str,
    source_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_storage_write),
) -> dict:
    try:
        return remove_workspace_confluence_source(workspace_id, source_id, user.user_id, user.email)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/confluence/sources/{source_id}/sync", response_model=WorkspaceConfluenceSourceResponse)
def sync_confluence_source(
    workspace_id: str,
    source_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_storage_write),
) -> dict:
    try:
        return sync_workspace_confluence_source(source_id, workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
