from __future__ import annotations

from urllib.parse import urlparse

from src.backend.infrastructure.ingestion.repo_manager import (
    RepoError,
    index_local_repo,
    index_repo,
    list_indexes,
)
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError
from src.backend.application.services.bitbucket_service import (
    can_user_access_bitbucket_repo,
    get_valid_bitbucket_access_token,
    require_user_can_access_bitbucket_repo,
)
from src.backend.application.services.github_service import get_valid_github_access_token
from src.backend.application.services.github_service import can_user_access_github_repo, require_user_can_access_github_repo
from src.backend.application.services.gitlab_service import (
    can_user_access_gitlab_project,
    get_valid_gitlab_access_token,
    require_user_can_access_gitlab_project,
)
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
    auth_token = None
    if workspace_id:
        if not user_id or not user_email or not user_can_manage_workspace_connectors(user_id, user_email, workspace_id):
            raise PermissionDeniedError("Connector manager access required.")
    if user_id:
        require_user_can_access_repo(user_id, normalized_url)
        auth_token = get_access_token_for_repo(user_id, normalized_url)
    try:
        github_token = auth_token if repo_host(normalized_url) == "github.com" else None
        return index_repo(
            normalized_url,
            refresh=refresh,
            workspace_id=workspace_id,
            github_token=github_token,
            auth_token=auth_token,
        )
    except RepoError as exc:
        raise ValidationError(str(exc)) from exc


def filter_repo_matches_for_user(user_id: str, matches: list[dict]) -> list[dict]:
    permitted: list[dict] = []
    access_by_repo: dict[str, bool] = {}
    for match in matches:
        if match.get("source_type", "repo") != "repo":
            permitted.append(match)
            continue
        repo_url = str(match.get("repo_url") or "")
        if not repo_url or repo_url.startswith("local://"):
            permitted.append(match)
            continue
        if repo_url not in access_by_repo:
            access_by_repo[repo_url] = can_user_access_repo(user_id, repo_url)
        if access_by_repo[repo_url]:
            permitted.append(match)
    return permitted


def require_user_can_access_repo(user_id: str, repo_url: str) -> None:
    host = repo_host(repo_url)
    if host == "github.com":
        require_user_can_access_github_repo(user_id, repo_url)
        return
    if host == "bitbucket.org":
        require_user_can_access_bitbucket_repo(user_id, repo_url)
        return
    if host == "gitlab.com":
        require_user_can_access_gitlab_project(user_id, repo_url)
        return
    raise ValidationError("Use a github.com, bitbucket.org, or gitlab.com repository URL.")


def can_user_access_repo(user_id: str, repo_url: str) -> bool:
    host = repo_host(repo_url)
    if host == "github.com":
        return can_user_access_github_repo(user_id, repo_url)
    if host == "bitbucket.org":
        return can_user_access_bitbucket_repo(user_id, repo_url)
    if host == "gitlab.com":
        return can_user_access_gitlab_project(user_id, repo_url)
    return False


def get_access_token_for_repo(user_id: str, repo_url: str) -> str:
    host = repo_host(repo_url)
    if host == "github.com":
        return get_valid_github_access_token(user_id)
    if host == "bitbucket.org":
        return get_valid_bitbucket_access_token(user_id)
    if host == "gitlab.com":
        return get_valid_gitlab_access_token(user_id)
    raise ValidationError("Use a github.com, bitbucket.org, or gitlab.com repository URL.")


def repo_host(repo_url: str) -> str:
    parsed = urlparse(repo_url.strip())
    return (parsed.hostname or "").lower()


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
