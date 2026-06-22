from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user, require_workspace_access
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import (
    AddWorkspaceSlackChannelRequest,
    LinkWorkspaceSlackTeamRequest,
    SlackChannelsResponse,
    SlackConnectionResponse,
    WorkspaceSlackSourceResponse,
    WorkspaceSlackSourcesResponse,
    WorkspaceSlackTeamResponse,
    WorkspaceSlackTeamsResponse,
)
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.connectors.oauth_core import oauth_states_match
from src.backend.application.services.exceptions import PermissionDeniedError, ServiceError, ValidationError
from src.backend.application.services.slack_service import (
    SLACK_OAUTH_STATE_TTL_SECONDS,
    add_workspace_slack_source,
    build_slack_authorize_url,
    create_slack_oauth_start,
    create_slack_oauth_state,
    disconnect_slack,
    exchange_slack_code_for_connection,
    get_slack_connection_status,
    link_workspace_slack_team_for_user,
    list_visible_slack_channels,
    list_workspace_slack_channels,
    list_workspace_slack_sources,
    list_workspace_slack_teams,
    remove_workspace_slack_source,
    sync_workspace_slack_source,
    unlink_workspace_slack_team,
)
from src.backend.application.services.workspace_service import user_can_access_workspace, user_can_manage_workspace_connectors

router = APIRouter(tags=["slack"])
SLACK_STATE_COOKIE_NAME = "readbase_slack_oauth_state"
SLACK_PKCE_COOKIE_NAME = "readbase_slack_pkce"
SLACK_RETURN_WORKSPACE_COOKIE_NAME = "readbase_slack_return_workspace"


@router.get("/me/integrations/slack/start")
def start_slack_connection(
    workspace_id: str | None = Query(default=None),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    start = create_slack_oauth_start()
    normalized_workspace_id = workspace_id.strip() if workspace_id else ""
    if not start.code_verifier:
        raise service_error_to_http(ValidationError("Slack OAuth PKCE verifier is missing."))
    try:
        authorize_url = build_slack_authorize_url(start.state, start.code_verifier)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(
        key=SLACK_STATE_COOKIE_NAME,
        value=start.state,
        max_age=SLACK_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    redirect.set_cookie(
        key=SLACK_PKCE_COOKIE_NAME,
        value=start.code_verifier,
        max_age=SLACK_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    if normalized_workspace_id and user_can_access_workspace(user.user_id, user.email, normalized_workspace_id):
        redirect.set_cookie(
            key=SLACK_RETURN_WORKSPACE_COOKIE_NAME,
            value=normalized_workspace_id,
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
    slack_pkce_cookie: str | None = Cookie(default=None, alias=SLACK_PKCE_COOKIE_NAME),
    slack_return_workspace_cookie: str | None = Cookie(default=None, alias=SLACK_RETURN_WORKSPACE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    return_workspace_id = slack_return_workspace_cookie.strip() if slack_return_workspace_cookie else ""
    redirect = slack_oauth_redirect("slack_connected", "1", return_workspace_id)
    redirect.delete_cookie(key=SLACK_STATE_COOKIE_NAME, path="/")
    redirect.delete_cookie(key=SLACK_PKCE_COOKIE_NAME, path="/")
    redirect.delete_cookie(key=SLACK_RETURN_WORKSPACE_COOKIE_NAME, path="/")
    if not code or not oauth_states_match(state, slack_state_cookie) or not slack_pkce_cookie:
        redirect = slack_oauth_redirect("slack_error", "invalid_state", return_workspace_id)
        redirect.delete_cookie(key=SLACK_STATE_COOKIE_NAME, path="/")
        redirect.delete_cookie(key=SLACK_PKCE_COOKIE_NAME, path="/")
        redirect.delete_cookie(key=SLACK_RETURN_WORKSPACE_COOKIE_NAME, path="/")
        return redirect
    try:
        result = exchange_slack_code_for_connection(
            user.user_id,
            code,
            workspace_id=return_workspace_id if return_workspace_id and user_can_access_workspace(user.user_id, user.email, return_workspace_id) else None,
            code_verifier=slack_pkce_cookie,
        )
    except ServiceError:
        redirect = slack_oauth_redirect("slack_error", "connect_failed", return_workspace_id)
        redirect.delete_cookie(key=SLACK_STATE_COOKIE_NAME, path="/")
        redirect.delete_cookie(key=SLACK_PKCE_COOKIE_NAME, path="/")
        redirect.delete_cookie(key=SLACK_RETURN_WORKSPACE_COOKIE_NAME, path="/")
        return redirect
    if result.get("already_connected"):
        redirect = slack_oauth_redirect("slack_connected", "already", return_workspace_id)
        redirect.delete_cookie(key=SLACK_STATE_COOKIE_NAME, path="/")
        redirect.delete_cookie(key=SLACK_PKCE_COOKIE_NAME, path="/")
        redirect.delete_cookie(key=SLACK_RETURN_WORKSPACE_COOKIE_NAME, path="/")
        return redirect
    return redirect


def slack_oauth_redirect(status_key: str, status_value: str, workspace_id: str = "") -> RedirectResponse:
    params = {
        status_key: status_value,
        "connector": "slack",
    }
    if workspace_id:
        params["workspace_id"] = workspace_id
    return RedirectResponse(url=f"/?{urllib.parse.urlencode(params)}", status_code=303)


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


@router.get("/workspaces/{workspace_id}/slack/teams", response_model=WorkspaceSlackTeamsResponse)
def workspace_slack_teams(
    workspace_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return {"teams": list_workspace_slack_teams(workspace_id, user.user_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/workspaces/{workspace_id}/slack/teams", response_model=WorkspaceSlackTeamResponse)
def link_slack_team(
    workspace_id: str,
    payload: LinkWorkspaceSlackTeamRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return link_workspace_slack_team_for_user(workspace_id, user.user_id, user.email, payload.team_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/workspaces/{workspace_id}/slack/teams/{team_id}", response_model=WorkspaceSlackTeamResponse)
def unlink_slack_team(
    workspace_id: str,
    team_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return unlink_workspace_slack_team(workspace_id, user.user_id, user.email, team_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/slack/channels", response_model=SlackChannelsResponse)
def workspace_slack_channels(
    workspace_id: str,
    query: str = Query(default=""),
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return {"channels": list_workspace_slack_channels(workspace_id, user.user_id, query=query)}
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
