from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import LinearVisibilityCache, utc_now

from .auth import get_valid_linear_access_token
from .constants import LINEAR_VISIBILITY_CACHE_TTL_SECONDS
from .http import linear_graphql_request
from src.backend.application.services.jira.utils import as_utc


def filter_linear_matches_for_user(user_id: str, matches: list[dict]) -> list[dict]:
    permitted: list[dict] = []
    access_by_issue: dict[str, bool] = {}
    for match in matches:
        if match.get("source_type") != "linear":
            permitted.append(match)
            continue
        issue_id = str(match.get("issue_id") or "")
        if not issue_id:
            continue
        if issue_id not in access_by_issue:
            access_by_issue[issue_id] = can_user_access_linear_issue(user_id, issue_id, str(match.get("item_type") or ""), str(match.get("item_id") or ""))
        if access_by_issue[issue_id]:
            permitted.append(match)
    return permitted


def can_user_access_linear_issue(user_id: str, issue_id: str, item_type: str = "issue", item_id: str = "") -> bool:
    cached = read_visibility_cache(user_id, issue_id, item_type, item_id or issue_id)
    if cached is not None:
        return cached
    try:
        token = get_valid_linear_access_token(user_id)
        data = linear_graphql_request("query($id: String!) { issue(id: $id) { id } }", token, {"id": issue_id})
        can_access = bool(data.get("issue"))
    except Exception:
        can_access = False
    write_visibility_cache(user_id, issue_id, item_type, item_id or issue_id, can_access)
    return can_access


def read_visibility_cache(user_id: str, issue_id: str, item_type: str, item_id: str) -> bool | None:
    now = utc_now()
    with session_scope() as session:
        cached = session.scalar(
            select(LinearVisibilityCache).where(
                LinearVisibilityCache.user_id == user_id,
                LinearVisibilityCache.issue_id == issue_id,
                LinearVisibilityCache.item_type == item_type,
                LinearVisibilityCache.item_id == item_id,
            )
        )
        if cached is None or as_utc(cached.expires_at) <= now:
            return None
        return bool(cached.can_access)


def write_visibility_cache(user_id: str, issue_id: str, item_type: str, item_id: str, can_access: bool) -> None:
    with session_scope() as session:
        cached = session.scalar(
            select(LinearVisibilityCache).where(
                LinearVisibilityCache.user_id == user_id,
                LinearVisibilityCache.issue_id == issue_id,
                LinearVisibilityCache.item_type == item_type,
                LinearVisibilityCache.item_id == item_id,
            )
        )
        if cached is None:
            cached = LinearVisibilityCache(user_id=user_id, issue_id=issue_id, item_type=item_type, item_id=item_id, can_access=can_access, expires_at=utc_now())
            session.add(cached)
        cached.can_access = can_access
        cached.checked_at = utc_now()
        cached.expires_at = utc_now() + timedelta(seconds=LINEAR_VISIBILITY_CACHE_TTL_SECONDS)
