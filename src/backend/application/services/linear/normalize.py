from __future__ import annotations

import hashlib
from datetime import datetime

from src.backend.infrastructure.models import WorkspaceLinearSource, utc_now


def normalize_issues(source: WorkspaceLinearSource, issues: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for issue in issues:
        issue_id = str(issue.get("id") or "")
        issue_key = str(issue.get("identifier") or issue_id)
        title = str(issue.get("title") or issue_key)
        description = str(issue.get("description") or "")
        url = str(issue.get("url") or "")
        if description:
            rows.append(item(source, issue_id, issue_key, "issue", issue_id, title, description, url, issue.get("updatedAt")))
        for comment in nodes(issue.get("comments")):
            body = str(comment.get("body") or "")
            comment_id = str(comment.get("id") or "")
            if body and comment_id:
                rows.append(item(source, issue_id, issue_key, "comment", comment_id, f"{issue_key} comment", body, url, comment.get("updatedAt")))
    return rows


def item(source: WorkspaceLinearSource, issue_id: str, issue_key: str, item_type: str, item_id: str, title: str, body: str, url: str, updated_at: object) -> dict:
    return {
        "source_id": source.source_id,
        "workspace_id": source.workspace_id,
        "linear_team_id": source.linear_team_id,
        "linear_project_id": source.linear_project_id,
        "issue_id": issue_id,
        "issue_key": issue_key,
        "item_type": item_type,
        "item_id": item_id,
        "title": title[:500],
        "body": body,
        "source_url": url,
        "remote_updated_at": parse_time(updated_at),
        "content_hash": hashlib.sha256(f"{title}\n{body}".encode("utf-8")).hexdigest(),
        "indexed_at": utc_now(),
    }


def nodes(value: object) -> list[dict]:
    if isinstance(value, dict) and isinstance(value.get("nodes"), list):
        return [node for node in value["nodes"] if isinstance(node, dict)]
    return []


def parse_time(value: object):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
