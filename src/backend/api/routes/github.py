from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import GithubConnectionResponse, GithubRepositoriesResponse
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.github_service import (
    GITHUB_OAUTH_STATE_TTL_SECONDS,
    build_github_authorize_url,
    create_github_oauth_state,
    disconnect_github,
    exchange_github_code_for_connection,
    get_github_connection_status,
    list_visible_github_repositories,
)

router = APIRouter(tags=["github"])
GITHUB_STATE_COOKIE_NAME = "readbase_github_oauth_state"


@router.get("/me/integrations/github/start")
def start_github_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_github_oauth_state()
    try:
        authorize_url = build_github_authorize_url(state)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(
        key=GITHUB_STATE_COOKIE_NAME,
        value=state,
        max_age=GITHUB_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    return redirect


@router.get("/me/integrations/github/callback")
def complete_github_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    github_state_cookie: str | None = Cookie(default=None, alias=GITHUB_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?github_connected=1", status_code=303)
    redirect.delete_cookie(key=GITHUB_STATE_COOKIE_NAME, path="/")
    if not code or not state or not github_state_cookie or state != github_state_cookie:
        redirect = RedirectResponse(url="/?github_error=invalid_state", status_code=303)
        redirect.delete_cookie(key=GITHUB_STATE_COOKIE_NAME, path="/")
        return redirect
    try:
        exchange_github_code_for_connection(user.user_id, code)
    except ServiceError:
        redirect = RedirectResponse(url="/?github_error=connect_failed", status_code=303)
        redirect.delete_cookie(key=GITHUB_STATE_COOKIE_NAME, path="/")
        return redirect
    return redirect


@router.get("/me/integrations/github", response_model=GithubConnectionResponse)
def github_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_github_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/me/integrations/github/repos", response_model=GithubRepositoriesResponse)
def github_repositories(
    query: str = Query(default=""),
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return {"repositories": list_visible_github_repositories(user.user_id, query=query)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/github", response_model=GithubConnectionResponse)
def disconnect_github_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return disconnect_github(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
