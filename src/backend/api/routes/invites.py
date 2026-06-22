from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import WorkspaceInviteListItemResponse, WorkspaceInvitesResponse
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.workspace_invite_service import (
    accept_workspace_invite,
    get_link_invite_preview,
    list_invites_for_user,
    reject_workspace_invite,
    revert_workspace_invite,
)

router = APIRouter(prefix="/invites", tags=["invites"])


@router.get("", response_model=WorkspaceInvitesResponse)
def list_invites_endpoint(user=Depends(require_authenticated_user)) -> dict:
    try:
        return list_invites_for_user(user.user_id, user.email)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/join/{join_token}", response_model=WorkspaceInviteListItemResponse)
def link_invite_preview_endpoint(
    join_token: str,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return get_link_invite_preview(user, join_token)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/{invite_id}/accept", response_model=WorkspaceInviteListItemResponse)
def accept_invite_endpoint(
    invite_id: str,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return accept_workspace_invite(user, invite_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/{invite_id}/reject", response_model=WorkspaceInviteListItemResponse)
def reject_invite_endpoint(
    invite_id: str,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return reject_workspace_invite(user, invite_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/{invite_id}/revert", response_model=WorkspaceInviteListItemResponse)
def revert_invite_endpoint(
    invite_id: str,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return revert_workspace_invite(user, invite_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
