from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import ConfluenceVisibilityCache, utc_now

from .auth import get_valid_confluence_access_token
from .constants import CONFLUENCE_VISIBILITY_CACHE_TTL_SECONDS
from .http import confluence_request
from src.backend.application.services.jira.utils import as_utc


def filter_confluence_matches_for_user(user_id: str, matches: list[dict]) -> list[dict]:
    permitted: list[dict] = []
    access_by_page: dict[tuple[str, str], bool] = {}
    for match in matches:
        if match.get("source_type") != "confluence":
            permitted.append(match)
            continue
        cloud_id = str(match.get("cloud_id") or "")
        page_id = str(match.get("page_id") or "")
        if not cloud_id or not page_id:
            continue
        key = (cloud_id, page_id)
        if key not in access_by_page:
            access_by_page[key] = can_user_access_confluence_page(user_id, cloud_id, page_id)
        if access_by_page[key]:
            permitted.append(match)
    return permitted


def can_user_access_confluence_page(user_id: str, cloud_id: str, page_id: str) -> bool:
    cached = read_visibility_cache(user_id, cloud_id, page_id)
    if cached is not None:
        return cached
    try:
        token = get_valid_confluence_access_token(user_id)
        confluence_request(cloud_id, f"/wiki/api/v2/pages/{page_id}", token)
        can_access = True
    except Exception:
        can_access = False
    write_visibility_cache(user_id, cloud_id, page_id, can_access)
    return can_access


def read_visibility_cache(user_id: str, cloud_id: str, page_id: str) -> bool | None:
    now = utc_now()
    with session_scope() as session:
        cached = session.scalar(
            select(ConfluenceVisibilityCache).where(
                ConfluenceVisibilityCache.user_id == user_id,
                ConfluenceVisibilityCache.cloud_id == cloud_id,
                ConfluenceVisibilityCache.page_id == page_id,
            )
        )
        if cached is None or as_utc(cached.expires_at) <= now:
            return None
        return bool(cached.can_access)


def write_visibility_cache(user_id: str, cloud_id: str, page_id: str, can_access: bool) -> None:
    with session_scope() as session:
        cached = session.scalar(
            select(ConfluenceVisibilityCache).where(
                ConfluenceVisibilityCache.user_id == user_id,
                ConfluenceVisibilityCache.cloud_id == cloud_id,
                ConfluenceVisibilityCache.page_id == page_id,
            )
        )
        if cached is None:
            cached = ConfluenceVisibilityCache(user_id=user_id, cloud_id=cloud_id, page_id=page_id, can_access=can_access, expires_at=utc_now())
            session.add(cached)
        cached.can_access = can_access
        cached.checked_at = utc_now()
        cached.expires_at = utc_now() + timedelta(seconds=CONFLUENCE_VISIBILITY_CACHE_TTL_SECONDS)
