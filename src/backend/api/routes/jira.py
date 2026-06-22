from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user, require_workspace_access
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import (
    AddWorkspaceJiraProjectRequest,
    ConnectWorkspaceJiraSiteRequest,
    JiraConnectionResponse,
    JiraProjectsResponse,
    WorkspaceJiraSiteStatusResponse,
    WorkspaceJiraSourceResponse,
    WorkspaceJiraSourcesResponse,
)
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.connectors.oauth_core import oauth_states_match
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.exceptions import PermissionDeniedError
from src.backend.application.services.jira_service import (
    JIRA_OAUTH_STATE_TTL_SECONDS,
    add_workspace_jira_source,
    build_jira_authorize_url,
    connect_workspace_jira_site,
    create_jira_oauth_state,
    disconnect_jira,
    exchange_jira_code_for_connection,
    get_jira_connection_status,
    get_workspace_jira_site,
    list_visible_jira_projects,
    list_workspace_jira_sources,
    remove_workspace_jira_site,
    remove_workspace_jira_source,
    sync_workspace_jira_source,
)
from src.backend.application.services.workspace_service import user_can_manage_workspace_connectors

router = APIRouter(tags=["jira"])
JIRA_STATE_COOKIE_NAME = "readbase_jira_oauth_state"


@router.get("/me/integrations/jira/start")
def start_jira_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_jira_oauth_state()
    redirect = RedirectResponse(url=build_jira_authorize_url(state), status_code=302)
    redirect.set_cookie(
        key=JIRA_STATE_COOKIE_NAME,
        value=state,
        max_age=JIRA_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    return redirect


@router.get("/me/integrations/jira/callback")
def complete_jira_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    jira_state_cookie: str | None = Cookie(default=None, alias=JIRA_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?jira_connected=1", status_code=303)
    redirect.delete_cookie(key=JIRA_STATE_COOKIE_NAME, path="/")
    if not code or not oauth_states_match(state, jira_state_cookie):
        return RedirectResponse(url="/?jira_error=invalid_state", status_code=303)
    try:
        exchange_jira_code_for_connection(user.user_id, code)
    except ServiceError:
        return RedirectResponse(url="/?jira_error=connect_failed", status_code=303)
    return redirect


@router.get("/me/integrations/jira", response_model=JiraConnectionResponse)
def jira_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_jira_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/jira", response_model=JiraConnectionResponse)
def disconnect_jira_connection(
    remove_data: bool = Query(default=False),
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return disconnect_jira(user.user_id, remove_data=remove_data)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/jira/site", response_model=WorkspaceJiraSiteStatusResponse)
def workspace_jira_site(
    workspace_id: str,
    _user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return get_workspace_jira_site(workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/jira/site", response_model=WorkspaceJiraSiteStatusResponse)
def connect_jira_site(
    workspace_id: str,
    payload: ConnectWorkspaceJiraSiteRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return connect_workspace_jira_site(workspace_id, user.user_id, user.email, payload.cloud_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/workspaces/{workspace_id}/jira/site", response_model=WorkspaceJiraSiteStatusResponse)
def disconnect_jira_site(
    workspace_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return remove_workspace_jira_site(workspace_id, user.user_id, user.email)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/jira/projects", response_model=JiraProjectsResponse)
def jira_projects(
    workspace_id: str,
    query: str = Query(default=""),
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        site_status = get_workspace_jira_site(workspace_id)
        if not site_status.get("connected") or not site_status.get("site"):
            return {"projects": []}
        cloud_id = str(site_status["site"]["cloud_id"])
        return {"projects": list_visible_jira_projects(user.user_id, query=query, cloud_id=cloud_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/jira/sources", response_model=WorkspaceJiraSourcesResponse)
def workspace_jira_sources(
    workspace_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return {"sources": list_workspace_jira_sources(workspace_id, user.user_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/jira/sources", response_model=WorkspaceJiraSourceResponse)
def add_jira_source(
    workspace_id: str,
    payload: AddWorkspaceJiraProjectRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return add_workspace_jira_source(workspace_id, user.user_id, user.email, payload.dict())
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/workspaces/{workspace_id}/jira/sources/{source_id}", response_model=WorkspaceJiraSourceResponse)
def delete_jira_source(
    workspace_id: str,
    source_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return remove_workspace_jira_source(workspace_id, source_id, user.user_id, user.email)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/jira/sources/{source_id}/sync", response_model=WorkspaceJiraSourceResponse)
def sync_jira_source(
    workspace_id: str,
    source_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        if not user_can_manage_workspace_connectors(user.user_id, user.email, workspace_id):
            raise PermissionDeniedError("Connector manager access required.")
        return sync_workspace_jira_source(source_id, workspace_id=workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
