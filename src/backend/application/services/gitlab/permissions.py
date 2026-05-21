from __future__ import annotations

import urllib.parse
from urllib.parse import urlparse

from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError

from .auth import get_valid_gitlab_access_token
from .http import gitlab_json_request


def can_user_access_gitlab_project(user_id: str, repo_url: str) -> bool:
    try:
        project_path = parse_gitlab_project_url(repo_url)
        token = get_valid_gitlab_access_token(user_id)
        encoded = urllib.parse.quote(project_path, safe="")
        gitlab_json_request(f"/projects/{encoded}", token=token)
        return True
    except Exception:
        return False


def require_user_can_access_gitlab_project(user_id: str, repo_url: str) -> None:
    if not can_user_access_gitlab_project(user_id, repo_url):
        raise PermissionDeniedError("Connect GitLab with access to this project before indexing it.")


def parse_gitlab_project_url(repo_url: str) -> str:
    parsed = urlparse(repo_url.strip())
    if (parsed.hostname or "").lower() != "gitlab.com":
        raise ValidationError("Use a gitlab.com project URL.")
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if "/" not in path:
        raise ValidationError("GitLab project URL must include namespace and project.")
    return path
