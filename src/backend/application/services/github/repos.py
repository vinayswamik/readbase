from __future__ import annotations

from urllib.parse import urlencode

from .auth import get_valid_github_access_token
from .http import github_json_request

MAX_REPO_SUGGESTIONS = 100


def list_visible_github_repositories(user_id: str, query: str = "") -> list[dict]:
    token = get_valid_github_access_token(user_id)
    normalized_query = query.strip().lower()
    repositories: list[dict] = []
    for page in range(1, 4):
        params = urlencode(
            {
                "affiliation": "owner,collaborator,organization_member",
                "visibility": "all",
                "sort": "updated",
                "per_page": "100",
                "page": str(page),
            }
        )
        payload = github_json_request(f"/user/repos?{params}", token=token)
        if not isinstance(payload, list):
            break
        for repo in payload:
            serialized = serialize_repository(repo)
            if matches_query(serialized, normalized_query):
                repositories.append(serialized)
            if len(repositories) >= MAX_REPO_SUGGESTIONS:
                return repositories
        if len(payload) < 100:
            break
    return repositories


def serialize_repository(repo: dict) -> dict:
    owner = repo.get("owner") if isinstance(repo.get("owner"), dict) else {}
    return {
        "id": str(repo.get("id") or repo.get("node_id") or repo.get("full_name") or ""),
        "name": str(repo.get("name") or ""),
        "full_name": str(repo.get("full_name") or ""),
        "html_url": str(repo.get("html_url") or ""),
        "private": bool(repo.get("private")),
        "description": optional_str(repo.get("description")),
        "owner_login": optional_str(owner.get("login")),
        "updated_at": optional_str(repo.get("updated_at")),
    }


def matches_query(repo: dict, query: str) -> bool:
    if not query:
        return True
    searchable = " ".join(
        str(repo.get(key) or "").lower()
        for key in ("name", "full_name", "description", "owner_login")
    )
    return query in searchable


def optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
