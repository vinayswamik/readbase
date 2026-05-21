from __future__ import annotations

from urllib.parse import urlencode

from .auth import get_valid_bitbucket_access_token
from .http import bitbucket_json_request

MAX_REPO_SUGGESTIONS = 100
MAX_WORKSPACES = 50


def list_visible_bitbucket_repositories(user_id: str, query: str = "") -> list[dict]:
    token = get_valid_bitbucket_access_token(user_id)
    normalized_query = query.strip().lower()
    repositories: list[dict] = []
    for workspace_slug in list_accessible_workspace_slugs(token):
        repositories.extend(list_workspace_repositories(token, workspace_slug, normalized_query))
        if len(repositories) >= MAX_REPO_SUGGESTIONS:
            return sorted_repositories(repositories[:MAX_REPO_SUGGESTIONS])
    return sorted_repositories(repositories)


def list_accessible_workspace_slugs(token: str) -> list[str]:
    slugs: list[str] = []
    url = f"/user/workspaces?{urlencode({'pagelen': '100'})}"
    for _ in range(5):
        payload = bitbucket_json_request(url, token=token)
        for item in payload.get("values", []) if isinstance(payload, dict) else []:
            workspace = item.get("workspace") if isinstance(item.get("workspace"), dict) else {}
            slug = str(workspace.get("slug") or "").strip()
            if slug:
                slugs.append(slug)
            if len(slugs) >= MAX_WORKSPACES:
                return list(dict.fromkeys(slugs))
        next_url = payload.get("next") if isinstance(payload, dict) else None
        if not next_url:
            break
        url = str(next_url)
    return list(dict.fromkeys(slugs))


def list_workspace_repositories(token: str, workspace_slug: str, query: str) -> list[dict]:
    repositories: list[dict] = []
    url = f"/repositories/{workspace_slug}?{urlencode({'pagelen': '100', 'sort': '-updated_on'})}"
    for _ in range(3):
        payload = bitbucket_json_request(url, token=token)
        for repo in payload.get("values", []) if isinstance(payload, dict) else []:
            serialized = serialize_repository(repo)
            if matches_query(serialized, query):
                repositories.append(serialized)
            if len(repositories) >= MAX_REPO_SUGGESTIONS:
                return repositories
        next_url = payload.get("next") if isinstance(payload, dict) else None
        if not next_url:
            break
        url = str(next_url)
    return repositories


def sorted_repositories(repositories: list[dict]) -> list[dict]:
    return sorted(repositories, key=lambda repo: str(repo.get("updated_at") or ""), reverse=True)


def serialize_repository(repo: dict) -> dict:
    workspace = repo.get("workspace") if isinstance(repo.get("workspace"), dict) else {}
    links = repo.get("links") if isinstance(repo.get("links"), dict) else {}
    html = links.get("html") if isinstance(links.get("html"), dict) else {}
    clones = links.get("clone") if isinstance(links.get("clone"), list) else []
    clone_url = ""
    for clone in clones:
        if isinstance(clone, dict) and clone.get("name") == "https":
            clone_url = str(clone.get("href") or "")
            break
    return {
        "id": str(repo.get("uuid") or repo.get("full_name") or ""),
        "name": str(repo.get("name") or ""),
        "full_name": str(repo.get("full_name") or ""),
        "html_url": str(html.get("href") or repo.get("website") or ""),
        "clone_url": clone_url,
        "private": bool(repo.get("is_private")),
        "description": optional_str(repo.get("description")),
        "workspace_slug": optional_str(workspace.get("slug")),
        "updated_at": optional_str(repo.get("updated_on")),
    }


def matches_query(repo: dict, query: str) -> bool:
    if not query:
        return True
    searchable = " ".join(str(repo.get(key) or "").lower() for key in ("name", "full_name", "description", "workspace_slug"))
    return query in searchable


def optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
