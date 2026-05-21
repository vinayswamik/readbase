from __future__ import annotations

from urllib.parse import urlparse

from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError

from .auth import get_valid_bitbucket_access_token
from .http import bitbucket_json_request


def can_user_access_bitbucket_repo(user_id: str, repo_url: str) -> bool:
    try:
        workspace, repo_slug = parse_bitbucket_repo_url(repo_url)
        token = get_valid_bitbucket_access_token(user_id)
        bitbucket_json_request(f"/repositories/{workspace}/{repo_slug}", token=token)
        return True
    except Exception:
        return False


def require_user_can_access_bitbucket_repo(user_id: str, repo_url: str) -> None:
    if not can_user_access_bitbucket_repo(user_id, repo_url):
        raise PermissionDeniedError("Connect Bitbucket with access to this repository before indexing it.")


def parse_bitbucket_repo_url(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url.strip())
    if (parsed.hostname or "").lower() != "bitbucket.org":
        raise ValidationError("Use a bitbucket.org repository URL.")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValidationError("Bitbucket repository URL must include workspace and repo.")
    repo = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    return parts[0], repo
