from __future__ import annotations

from src.backend.infrastructure.ingestion.repo_manager import (
    RepoError,
    index_local_repo,
    index_repo,
    list_indexes,
)
from src.backend.application.services.exceptions import ValidationError


def list_repositories(workspace_id: str | None = None) -> list[dict]:
    return list_indexes(workspace_id=workspace_id)


def index_repository(
    repo_url: str,
    refresh: bool = False,
    workspace_id: str | None = None,
) -> dict:
    normalized_url = repo_url.strip()
    if not normalized_url:
        raise ValidationError("repo_url is required.")
    try:
        return index_repo(normalized_url, refresh=refresh, workspace_id=workspace_id)
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
