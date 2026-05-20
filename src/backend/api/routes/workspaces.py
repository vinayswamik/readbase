from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Depends

from src.backend.api.auth import (
    require_admin_user,
    require_authenticated_user,
    require_workspace_access,
    require_workspace_owner,
)
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import (
    AskRequest,
    AskResponse,
    CreateWorkspaceRequest,
    IndexedRepoResponse,
    IndexRequest,
    AddWorkspaceMemberRequest,
    WorkspaceMemberResponse,
    WorkspaceMembersResponse,
    UpdateWorkspaceConnectorRequest,
    WorkspaceConnectorResponse,
    WorkspaceConnectorsResponse,
    ReposResponse,
    WorkspaceResponse,
    WorkspacesResponse,
)
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.question_service import ask_repository_question
from src.backend.application.services.repo_service import index_repository, list_repositories
from src.backend.application.services.workspace_service import (
    create_workspace,
    delete_workspace,
    add_workspace_member,
    list_workspace_connectors,
    list_workspace_members,
    list_workspaces,
    remove_workspace_member,
    update_workspace_connector,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=WorkspacesResponse)
def workspaces(user=Depends(require_authenticated_user)) -> dict:
    try:
        return {
            "workspaces": list_workspaces(
                user.user_id,
                user_email=user.email,
                user_role=user.role,
            )
        }
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("", response_model=WorkspaceResponse)
def create_workspace_endpoint(
    payload: CreateWorkspaceRequest,
    user=Depends(require_admin_user),
) -> dict:
    try:
        return create_workspace(
            user.user_id,
            payload.name,
            owner_email=user.email,
            owner_name=user.name,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/{workspace_id}", response_model=WorkspaceResponse)
def delete_workspace_endpoint(
    workspace_id: str,
    user=Depends(require_admin_user),
    _workspace=Depends(require_workspace_owner),
) -> dict:
    try:
        return delete_workspace(user.user_id, workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/{workspace_id}/repos", response_model=ReposResponse)
def workspace_repos(
    workspace_id: str,
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return {"repos": list_repositories(workspace_id=workspace_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/{workspace_id}/index", response_model=IndexedRepoResponse)
def workspace_index_endpoint(
    workspace_id: str,
    payload: IndexRequest,
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return index_repository(
            payload.repo_url,
            refresh=payload.refresh,
            workspace_id=workspace_id,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/{workspace_id}/ask", response_model=AskResponse)
def workspace_ask_endpoint(
    workspace_id: str,
    payload: AskRequest,
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return ask_repository_question(
            repo_id=payload.repo_id,
            question=payload.question,
            top_k=payload.top_k,
            workspace_id=workspace_id,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/{workspace_id}/members", response_model=WorkspaceMembersResponse)
def workspace_members(
    workspace_id: str,
    user=Depends(require_admin_user),
    _workspace=Depends(require_workspace_owner),
) -> dict:
    try:
        return {"members": list_workspace_members(user.user_id, workspace_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/{workspace_id}/connectors", response_model=WorkspaceConnectorsResponse)
def workspace_connectors(
    workspace_id: str,
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return list_workspace_connectors(workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.patch("/{workspace_id}/connectors/{connector_id}", response_model=WorkspaceConnectorResponse)
def update_connector_endpoint(
    workspace_id: str,
    connector_id: str,
    payload: UpdateWorkspaceConnectorRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return update_workspace_connector(
            workspace_id,
            connector_id,
            payload.enabled,
            updated_by_user_id=user.user_id,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse)
def add_member_endpoint(
    workspace_id: str,
    payload: AddWorkspaceMemberRequest,
    user=Depends(require_admin_user),
    _workspace=Depends(require_workspace_owner),
) -> dict:
    try:
        return add_workspace_member(user.user_id, workspace_id, payload.email)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/{workspace_id}/members/{email:path}", response_model=WorkspaceMemberResponse)
def remove_member_endpoint(
    workspace_id: str,
    email: str,
    user=Depends(require_admin_user),
    _workspace=Depends(require_workspace_owner),
) -> dict:
    try:
        return remove_workspace_member(user.user_id, workspace_id, unquote(email))
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
