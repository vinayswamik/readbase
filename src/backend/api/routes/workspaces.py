from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import (
    AskRequest,
    AskResponse,
    CreateWorkspaceRequest,
    IndexedRepoResponse,
    IndexRequest,
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
    get_workspace,
    list_workspaces,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=WorkspacesResponse)
def workspaces(user=Depends(require_authenticated_user)) -> dict:
    try:
        return {"workspaces": list_workspaces(user.user_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("", response_model=WorkspaceResponse)
def create_workspace_endpoint(
    payload: CreateWorkspaceRequest,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return create_workspace(user.user_id, payload.name)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/{workspace_id}", response_model=WorkspaceResponse)
def delete_workspace_endpoint(
    workspace_id: str,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return delete_workspace(user.user_id, workspace_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/{workspace_id}/repos", response_model=ReposResponse)
def workspace_repos(
    workspace_id: str,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        get_workspace(user.user_id, workspace_id)
        return {"repos": list_repositories(workspace_id=workspace_id)}
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/{workspace_id}/index", response_model=IndexedRepoResponse)
def workspace_index_endpoint(
    workspace_id: str,
    payload: IndexRequest,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        get_workspace(user.user_id, workspace_id)
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
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        get_workspace(user.user_id, workspace_id)
        return ask_repository_question(
            repo_id=payload.repo_id,
            question=payload.question,
            top_k=payload.top_k,
            workspace_id=workspace_id,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
