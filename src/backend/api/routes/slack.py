from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user, require_workspace_access
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import (
    AddWorkspaceSlackChannelRequest,
    SlackChannelsResponse,
    SlackConnectionResponse,
    WorkspaceSlackSourceResponse,
    WorkspaceSlackSourcesResponse,
)
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.exceptions import PermissionDeniedError, ServiceError
from src.backend.application.services.slack_service import (
    SLACK_OAUTH_STATE_TTL_SECONDS,
    add_workspace_slack_source,
    build_slack_authorize_url,
    create_slack_oauth_state,
    disconnect_slack,
    exchange_slack_code_for_connection,
    get_slack_connection_status,
    list_visible_slack_channels,
    list_workspace_slack_sources,
    remove_workspace_slack_source,
    sync_workspace_slack_source,
)
from src.backend.application.services.workspace_service import user_can_manage_workspace_connectors

router = APIRouter(tags=["slack"])
SLACK_STATE_COOKIE_NAME = "readbase_slack_oauth_state"


@router.get("/me/integrations/slack/start")
def start_slack_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_slack_oauth_state()
    try:
        authorize_url = build_slack_authorize_url(state)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(
        key=SLACK_STATE_COOKIE_NAME,
        value=state,
        max_age=SLACK_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    return redirect


@router.get("/me/integrations/slack/callback")
def complete_slack_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    slack_state_cookie: str | None = Cookie(default=None, alias=SLACK_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?slack_connected=1", status_code=303)
    redirect.delete_cookie(key=SLACK_STATE_COOKIE_NAME, path="/")
    if not code or not state or not slack_state_cookie or state != slack_state_cookie:
        redirect = RedirectResponse(url="/?slack_error=invalid_state", status_code=303)
        redirect.delete_cookie(key=SLACK_STATE_COOKIE_NAME, path="/")
        return redirect
    try:
        exchange_slack_code_for_connection(user.user_id, code)
    except ServiceError:
        redirect = RedirectResponse(url="/?slack_error=connect_failed", status_code=303)
        redirect.delete_cookie(key=SLACK_STATE_COOKIE_NAME, path="/")
        return redirect
    return redirect


@router.get("/me/integrations/slack", response_model=SlackConnectionResponse)
def slack_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_slack_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/slack", response_model=SlackConnectionResponse)
def disconnect_slack_connection(
    team_id: str | None = Query(default=None),
    remove_data: bool = Query(default=False),
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return disconnect_slack(user.user_id, team_id=team_id, remove_data=remove_data)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/me/integrations/slack/channels", response_model=SlackChannelsResponse)
def slack_channels(
    team_id: str = Query(...),
    query: str = Query(default=""),
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return {"channels": list_visible_slack_channels(user.user_id, team_id=team_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/slack/sources", response_model=WorkspaceSlackSourcesResponse)
def workspace_slack_sources(
    workspace_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return {"sources": list_workspace_slack_sources(workspace_id, user.user_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/slack/sources", response_model=WorkspaceSlackSourceResponse)
def add_slack_source(
    workspace_id: str,
    payload: AddWorkspaceSlackChannelRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return add_workspace_slack_source(workspace_id, user.user_id, user.email, payload.dict())
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/workspaces/{workspace_id}/slack/sources/{source_id}", response_model=WorkspaceSlackSourceResponse)
def delete_slack_source(
    workspace_id: str,
    source_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return remove_workspace_slack_source(workspace_id, source_id, user.user_id, user.email)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/slack/sources/{source_id}/sync", response_model=WorkspaceSlackSourceResponse)
def sync_slack_source(
    workspace_id: str,
    source_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        if not user_can_manage_workspace_connectors(user.user_id, user.email, workspace_id):
            raise PermissionDeniedError("Connector manager access required.")
        return sync_workspace_slack_source(source_id, workspace_id=workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
