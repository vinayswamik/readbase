from __future__ import annotations

from urllib.parse import urlparse

from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError

from .auth import get_valid_github_access_token
from .http import github_json_request


def filter_repo_matches_for_user(user_id: str, matches: list[dict]) -> list[dict]:
    permitted: list[dict] = []
    access_by_repo: dict[str, bool] = {}
    for match in matches:
        if match.get("source_type", "repo") != "repo":
            permitted.append(match)
            continue
        repo_url = str(match.get("repo_url") or "")
        if not repo_url.startswith("https://github.com/"):
            permitted.append(match)
            continue
        if repo_url not in access_by_repo:
            access_by_repo[repo_url] = can_user_access_github_repo(user_id, repo_url)
        if access_by_repo[repo_url]:
            permitted.append(match)
    return permitted


def can_user_access_github_repo(user_id: str, repo_url: str) -> bool:
    try:
        owner, repo = parse_github_repo_url(repo_url)
        token = get_valid_github_access_token(user_id)
        github_json_request(f"/repos/{owner}/{repo}", token=token)
        return True
    except Exception:
        return False


def require_user_can_access_github_repo(user_id: str, repo_url: str) -> None:
    if not can_user_access_github_repo(user_id, repo_url):
        raise PermissionDeniedError("Connect GitHub with access to this repository before indexing it.")


def parse_github_repo_url(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url.strip())
    if parsed.netloc.lower() != "github.com":
        raise ValidationError("Use a github.com repository URL.")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValidationError("GitHub repository URL must include owner and repo.")
    repo = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    return parts[0], repo
