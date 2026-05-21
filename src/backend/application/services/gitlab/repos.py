from __future__ import annotations

from urllib.parse import urlencode

from .auth import get_valid_gitlab_access_token
from .http import gitlab_json_request

MAX_PROJECT_SUGGESTIONS = 100


def list_visible_gitlab_projects(user_id: str, query: str = "") -> list[dict]:
    token = get_valid_gitlab_access_token(user_id)
    projects: list[dict] = []
    for page in range(1, 4):
        params = {
            "membership": "true",
            "simple": "true",
            "order_by": "last_activity_at",
            "sort": "desc",
            "per_page": "100",
            "page": str(page),
        }
        if query.strip():
            params["search"] = query.strip()
        payload = gitlab_json_request(f"/projects?{urlencode(params)}", token=token)
        if not isinstance(payload, list):
            break
        for project in payload:
            projects.append(serialize_project(project))
            if len(projects) >= MAX_PROJECT_SUGGESTIONS:
                return projects
        if len(payload) < 100:
            break
    return projects


def serialize_project(project: dict) -> dict:
    namespace = project.get("namespace") if isinstance(project.get("namespace"), dict) else {}
    return {
        "id": str(project.get("id") or ""),
        "name": str(project.get("name") or ""),
        "path_with_namespace": str(project.get("path_with_namespace") or ""),
        "web_url": str(project.get("web_url") or ""),
        "clone_url": str(project.get("http_url_to_repo") or ""),
        "visibility": str(project.get("visibility") or ""),
        "description": optional_str(project.get("description")),
        "namespace": optional_str(namespace.get("full_path") or namespace.get("name")),
        "updated_at": optional_str(project.get("last_activity_at")),
    }


def optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
