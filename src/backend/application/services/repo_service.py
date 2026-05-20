from __future__ import annotations

from src.backend.infrastructure.ingestion.repo_manager import (
    RepoError,
    index_local_repo,
    index_repo,
    list_indexes,
)
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.application.services.github_service import get_valid_github_access_token
from src.backend.application.services.github_service import require_user_can_access_github_repo
from src.backend.application.services.workspace_connector_permissions import user_can_manage_workspace_connectors


def list_repositories(workspace_id: str | None = None) -> list[dict]:
    return list_indexes(workspace_id=workspace_id)


def index_repository(
    repo_url: str,
    refresh: bool = False,
    workspace_id: str | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
) -> dict:
    normalized_url = repo_url.strip()
    if not normalized_url:
        raise ValidationError("repo_url is required.")
    github_token = None
    if workspace_id:
        if not user_id or not user_email or not user_can_manage_workspace_connectors(user_id, user_email, workspace_id):
            raise PermissionDeniedError("Connector manager access required.")
    if user_id:
        require_user_can_access_github_repo(user_id, normalized_url)
        github_token = get_valid_github_access_token(user_id)
    try:
        return index_repo(normalized_url, refresh=refresh, workspace_id=workspace_id, github_token=github_token)
    except RepoError as exc:
        raise ValidationError(str(exc)) from exc


def index_local_repository(
    local_path: str,
    refresh: bool = False,
    workspace_id: str | None = None,
) -> dict:
    normalized_path = local_path.strip()
    if not normalized_path:
        raise ValidationError("local repository path is required.")
    try:
        return index_local_repo(normalized_path, refresh=refresh, workspace_id=workspace_id)
    except RepoError as exc:
        raise ValidationError(str(exc)) from exc
