from __future__ import annotations

import urllib.parse
from datetime import timedelta

from sqlalchemy import select

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import JiraVisibilityCache, utc_now

from .auth import get_valid_jira_access_token
from .constants import JIRA_VISIBILITY_CACHE_TTL_SECONDS
from .http import jira_request
from .utils import as_utc


def filter_jira_matches_for_user(user_id: str, matches: list[dict]) -> list[dict]:
    permitted: list[dict] = []
    for match in matches:
        if match.get("source_type") != "jira":
            permitted.append(match)
            continue
        if can_user_access_jira_match(user_id, match):
            permitted.append(match)
    return permitted


def can_user_access_jira_match(user_id: str, match: dict) -> bool:
    cloud_id = str(match.get("cloud_id") or "")
    issue_id = str(match.get("issue_id") or "")
    item_type = str(match.get("item_type") or "issue")
    item_id = str(match.get("item_id") or issue_id)
    if not cloud_id or not issue_id:
        return False
    cached = read_visibility_cache(user_id, cloud_id, issue_id, item_type, item_id)
    if cached is not None:
        return cached
    try:
        token = get_valid_jira_access_token(user_id)
        can_access = verify_jira_item_access(token, cloud_id, issue_id, item_type, item_id)
    except Exception:
        can_access = False
    write_visibility_cache(user_id, cloud_id, issue_id, item_type, item_id, can_access)
    return can_access


def verify_jira_item_access(token: str, cloud_id: str, issue_id: str, item_type: str, item_id: str) -> bool:
    if item_type == "comment":
        path = f"/rest/api/3/issue/{urllib.parse.quote(issue_id)}/comment/{urllib.parse.quote(item_id)}"
    elif item_type == "worklog":
        path = f"/rest/api/3/issue/{urllib.parse.quote(issue_id)}/worklog/{urllib.parse.quote(item_id)}"
    elif item_type == "attachment":
        path = f"/rest/api/3/attachment/{urllib.parse.quote(item_id)}"
    else:
        path = f"/rest/api/3/issue/{urllib.parse.quote(issue_id)}"
    try:
        jira_request(cloud_id, path, token, query={"fields": "summary"})
        return True
    except PermissionDeniedError:
        return False
    except ResourceNotFoundError:
        return False


def read_visibility_cache(user_id: str, cloud_id: str, issue_id: str, item_type: str, item_id: str) -> bool | None:
    now = utc_now()
    with session_scope() as session:
        cached = session.scalar(
            select(JiraVisibilityCache).where(
                JiraVisibilityCache.user_id == user_id,
                JiraVisibilityCache.cloud_id == cloud_id,
                JiraVisibilityCache.issue_id == issue_id,
                JiraVisibilityCache.item_type == item_type,
                JiraVisibilityCache.item_id == item_id,
            )
        )
        if cached is None or as_utc(cached.expires_at) <= now:
            return None
        return bool(cached.can_access)


def write_visibility_cache(
    user_id: str,
    cloud_id: str,
    issue_id: str,
    item_type: str,
    item_id: str,
    can_access: bool,
) -> None:
    with session_scope() as session:
        cached = session.scalar(
            select(JiraVisibilityCache).where(
                JiraVisibilityCache.user_id == user_id,
                JiraVisibilityCache.cloud_id == cloud_id,
                JiraVisibilityCache.issue_id == issue_id,
                JiraVisibilityCache.item_type == item_type,
                JiraVisibilityCache.item_id == item_id,
            )
        )
        if cached is None:
            cached = JiraVisibilityCache(
                user_id=user_id,
                cloud_id=cloud_id,
                issue_id=issue_id,
                item_type=item_type,
                item_id=item_id,
                can_access=can_access,
                expires_at=utc_now(),
            )
            session.add(cached)
        cached.can_access = can_access
        cached.checked_at = utc_now()
        cached.expires_at = utc_now() + timedelta(seconds=JIRA_VISIBILITY_CACHE_TTL_SECONDS)
