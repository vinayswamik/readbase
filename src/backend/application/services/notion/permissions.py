from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import NotionVisibilityCache, utc_now

from .auth import get_valid_notion_access_token
from .constants import NOTION_VISIBILITY_CACHE_TTL_SECONDS
from .http import notion_request
from src.backend.application.services.jira.utils import as_utc


def filter_notion_matches_for_user(user_id: str, matches: list[dict]) -> list[dict]:
    permitted: list[dict] = []
    access_by_page: dict[str, bool] = {}
    for match in matches:
        if match.get("source_type") != "notion":
            permitted.append(match)
            continue
        page_id = str(match.get("page_id") or "")
        if not page_id:
            continue
        if page_id not in access_by_page:
            access_by_page[page_id] = can_user_access_notion_page(user_id, page_id)
        if access_by_page[page_id]:
            permitted.append(match)
    return permitted


def can_user_access_notion_page(user_id: str, page_id: str) -> bool:
    cached = read_visibility_cache(user_id, page_id)
    if cached is not None:
        return cached
    try:
        token = get_valid_notion_access_token(user_id)
        notion_request(f"/pages/{page_id}", token)
        can_access = True
    except Exception:
        can_access = False
    write_visibility_cache(user_id, page_id, can_access)
    return can_access


def read_visibility_cache(user_id: str, page_id: str) -> bool | None:
    now = utc_now()
    with session_scope() as session:
        cached = session.scalar(
            select(NotionVisibilityCache).where(
                NotionVisibilityCache.user_id == user_id,
                NotionVisibilityCache.page_id == page_id,
            )
        )
        if cached is None or as_utc(cached.expires_at) <= now:
            return None
        return bool(cached.can_access)


def write_visibility_cache(user_id: str, page_id: str, can_access: bool) -> None:
    with session_scope() as session:
        cached = session.scalar(
            select(NotionVisibilityCache).where(
                NotionVisibilityCache.user_id == user_id,
                NotionVisibilityCache.page_id == page_id,
            )
        )
        if cached is None:
            cached = NotionVisibilityCache(user_id=user_id, page_id=page_id, can_access=can_access, expires_at=utc_now())
            session.add(cached)
        cached.can_access = can_access
        cached.checked_at = utc_now()
        cached.expires_at = utc_now() + timedelta(seconds=NOTION_VISIBILITY_CACHE_TTL_SECONDS)
