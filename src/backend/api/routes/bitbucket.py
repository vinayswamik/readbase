from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import BitbucketConnectionResponse, BitbucketRepositoriesResponse
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.bitbucket_service import (
    BITBUCKET_OAUTH_STATE_TTL_SECONDS,
    build_bitbucket_authorize_url,
    create_bitbucket_oauth_state,
    disconnect_bitbucket,
    exchange_bitbucket_code_for_connection,
    get_bitbucket_connection_status,
    list_visible_bitbucket_repositories,
)
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.workspace_service import user_can_access_workspace

router = APIRouter(tags=["bitbucket"])
BITBUCKET_STATE_COOKIE_NAME = "readbase_bitbucket_oauth_state"


@router.get("/me/integrations/bitbucket/start")
def start_bitbucket_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_bitbucket_oauth_state()
    try:
        authorize_url = build_bitbucket_authorize_url(state)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(BITBUCKET_STATE_COOKIE_NAME, state, max_age=BITBUCKET_OAUTH_STATE_TTL_SECONDS, httponly=True, samesite="lax", secure=SESSION_SECURE_COOKIE, path="/")
    return redirect


@router.get("/me/integrations/bitbucket/callback")
def complete_bitbucket_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    bitbucket_state_cookie: str | None = Cookie(default=None, alias=BITBUCKET_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?bitbucket_connected=1", status_code=303)
    redirect.delete_cookie(key=BITBUCKET_STATE_COOKIE_NAME, path="/")
    if not code or not state or not bitbucket_state_cookie or state != bitbucket_state_cookie:
        return RedirectResponse(url="/?bitbucket_error=invalid_state", status_code=303)
    try:
        exchange_bitbucket_code_for_connection(user.user_id, code)
    except ServiceError:
        return RedirectResponse(url="/?bitbucket_error=connect_failed", status_code=303)
    return redirect


@router.get("/me/integrations/bitbucket", response_model=BitbucketConnectionResponse)
def bitbucket_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_bitbucket_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/bitbucket", response_model=BitbucketConnectionResponse)
def disconnect_bitbucket_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return disconnect_bitbucket(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/me/integrations/bitbucket/repos", response_model=BitbucketRepositoriesResponse)
def bitbucket_repositories(query: str = Query(default=""), user=Depends(require_authenticated_user)) -> dict:
    try:
        return {"repositories": list_visible_bitbucket_repositories(user.user_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/workspaces/{workspace_id}/bitbucket/repos", response_model=BitbucketRepositoriesResponse)
def workspace_bitbucket_repositories(workspace_id: str, query: str = Query(default=""), user=Depends(require_authenticated_user)) -> dict:
    if not user_can_access_workspace(user.user_id, user.email, workspace_id):
        from src.backend.application.services.exceptions import PermissionDeniedError

        raise service_error_to_http(PermissionDeniedError("Workspace access required."))
    try:
        return {"repositories": list_visible_bitbucket_repositories(user.user_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
