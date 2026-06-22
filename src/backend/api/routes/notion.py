from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user, require_workspace_access, require_workspace_storage_write
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import (
    AddWorkspaceNotionDatabaseRequest,
    NotionConnectionResponse,
    NotionDatabasesResponse,
    WorkspaceNotionSourceResponse,
    WorkspaceNotionSourcesResponse,
)
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.connectors.oauth_core import oauth_states_match
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.notion_service import (
    NOTION_OAUTH_STATE_TTL_SECONDS,
    add_workspace_notion_source,
    build_notion_authorize_url,
    create_notion_oauth_state,
    disconnect_notion,
    exchange_notion_code_for_connection,
    get_notion_connection_status,
    list_visible_notion_databases,
    list_workspace_notion_sources,
    remove_workspace_notion_source,
    sync_workspace_notion_source,
)

router = APIRouter(tags=["notion"])
NOTION_STATE_COOKIE_NAME = "readbase_notion_oauth_state"


@router.get("/me/integrations/notion/start")
def start_notion_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_notion_oauth_state()
    try:
        authorize_url = build_notion_authorize_url(state)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(
        NOTION_STATE_COOKIE_NAME,
        state,
        max_age=NOTION_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    return redirect


@router.get("/me/integrations/notion/callback")
def complete_notion_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    notion_state_cookie: str | None = Cookie(default=None, alias=NOTION_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?notion_connected=1", status_code=303)
    redirect.delete_cookie(key=NOTION_STATE_COOKIE_NAME, path="/")
    if not code or not oauth_states_match(state, notion_state_cookie):
        return RedirectResponse(url="/?notion_error=invalid_state", status_code=303)
    try:
        exchange_notion_code_for_connection(user.user_id, code)
    except ServiceError:
        return RedirectResponse(url="/?notion_error=connect_failed", status_code=303)
    return redirect


@router.get("/me/integrations/notion", response_model=NotionConnectionResponse)
def notion_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_notion_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/notion", response_model=NotionConnectionResponse)
def disconnect_notion_connection(
    remove_data: bool = Query(default=False),
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return disconnect_notion(user.user_id, remove_data=remove_data)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/me/integrations/notion/databases", response_model=NotionDatabasesResponse)
def notion_databases(query: str = Query(default=""), user=Depends(require_authenticated_user)) -> dict:
    try:
        return {"databases": list_visible_notion_databases(user.user_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/notion/sources", response_model=WorkspaceNotionSourcesResponse)
def workspace_notion_sources(
    workspace_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return {"sources": list_workspace_notion_sources(workspace_id, user.user_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/notion/sources", response_model=WorkspaceNotionSourceResponse)
def add_notion_source(
    workspace_id: str,
    payload: AddWorkspaceNotionDatabaseRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_storage_write),
) -> dict:
    try:
        return add_workspace_notion_source(workspace_id, user.user_id, user.email, payload.dict())
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/workspaces/{workspace_id}/notion/sources/{source_id}", response_model=WorkspaceNotionSourceResponse)
def remove_notion_source(
    workspace_id: str,
    source_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_storage_write),
) -> dict:
    try:
        return remove_workspace_notion_source(workspace_id, source_id, user.user_id, user.email)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/notion/sources/{source_id}/sync", response_model=WorkspaceNotionSourceResponse)
def sync_notion_source(
    workspace_id: str,
    source_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_storage_write),
) -> dict:
    try:
        return sync_workspace_notion_source(source_id, workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
