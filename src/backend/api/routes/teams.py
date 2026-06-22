from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import TeamsConnectionResponse
from src.backend.application.services.auth_service import SESSION_SECURE_COOKIE
from src.backend.application.services.connectors.oauth_core import oauth_states_match
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.teams_service import (
    TEAMS_OAUTH_STATE_TTL_SECONDS,
    build_teams_authorize_url,
    create_teams_oauth_state,
    disconnect_teams,
    exchange_teams_code_for_connection,
    get_teams_connection_status,
)

router = APIRouter(tags=["teams"])
TEAMS_STATE_COOKIE_NAME = "readbase_teams_oauth_state"


@router.get("/me/integrations/teams/start")
def start_teams_connection(_user=Depends(require_authenticated_user)) -> RedirectResponse:
    state = create_teams_oauth_state()
    try:
        authorize_url = build_teams_authorize_url(state)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
    redirect = RedirectResponse(url=authorize_url, status_code=302)
    redirect.set_cookie(
        key=TEAMS_STATE_COOKIE_NAME,
        value=state,
        max_age=TEAMS_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_SECURE_COOKIE,
        path="/",
    )
    return redirect


@router.get("/me/integrations/teams/callback")
def complete_teams_connection(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    teams_state_cookie: str | None = Cookie(default=None, alias=TEAMS_STATE_COOKIE_NAME),
    user=Depends(require_authenticated_user),
) -> RedirectResponse:
    redirect = RedirectResponse(url="/?teams_connected=1", status_code=303)
    redirect.delete_cookie(key=TEAMS_STATE_COOKIE_NAME, path="/")
    if not code or not oauth_states_match(state, teams_state_cookie):
        return RedirectResponse(url="/?teams_error=invalid_state", status_code=303)
    try:
        exchange_teams_code_for_connection(user.user_id, code)
    except ServiceError:
        return RedirectResponse(url="/?teams_error=connect_failed", status_code=303)
    return redirect


@router.get("/me/integrations/teams", response_model=TeamsConnectionResponse)
def teams_connection(user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_teams_connection_status(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/me/integrations/teams", response_model=TeamsConnectionResponse)
def disconnect_teams_connection(
    remove_data: bool = Query(default=False),
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return disconnect_teams(user.user_id, remove_data=remove_data)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
