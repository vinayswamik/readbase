from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import SlackVisibilityCache, utc_now

from .auth import get_valid_slack_access_token
from .constants import SLACK_VISIBILITY_CACHE_TTL_SECONDS
from .http import slack_api_request
from .utils import as_utc


def filter_slack_matches_for_user(user_id: str, matches: list[dict]) -> list[dict]:
    permitted: list[dict] = []
    access_by_channel: dict[tuple[str, str], bool] = {}
    for match in matches:
        if match.get("source_type") != "slack":
            permitted.append(match)
            continue
        team_id = str(match.get("team_id") or "")
        channel_id = str(match.get("channel_id") or "")
        if not team_id or not channel_id:
            continue
        key = (team_id, channel_id)
        if key not in access_by_channel:
            access_by_channel[key] = can_user_access_slack_channel(user_id, team_id, channel_id)
        if access_by_channel[key]:
            permitted.append(match)
    return permitted


def can_user_access_slack_channel(user_id: str, team_id: str, channel_id: str) -> bool:
    cached = read_visibility_cache(user_id, team_id, channel_id)
    if cached is not None:
        return cached
    try:
        token = get_valid_slack_access_token(user_id, team_id)
        can_access = verify_slack_channel_access(token, channel_id)
    except Exception:
        can_access = False
    write_visibility_cache(user_id, team_id, channel_id, can_access)
    return can_access


def verify_slack_channel_access(token: str, channel_id: str) -> bool:
    slack_api_request("/conversations.info", token=token, query={"channel": channel_id})
    return True


def read_visibility_cache(user_id: str, team_id: str, channel_id: str) -> bool | None:
    now = utc_now()
    with session_scope() as session:
        cached = session.scalar(
            select(SlackVisibilityCache).where(
                SlackVisibilityCache.user_id == user_id,
                SlackVisibilityCache.team_id == team_id,
                SlackVisibilityCache.channel_id == channel_id,
            )
        )
        if cached is None or as_utc(cached.expires_at) <= now:
            return None
        return bool(cached.can_access)


def write_visibility_cache(user_id: str, team_id: str, channel_id: str, can_access: bool) -> None:
    with session_scope() as session:
        cached = session.scalar(
            select(SlackVisibilityCache).where(
                SlackVisibilityCache.user_id == user_id,
                SlackVisibilityCache.team_id == team_id,
                SlackVisibilityCache.channel_id == channel_id,
            )
        )
        if cached is None:
            cached = SlackVisibilityCache(
                user_id=user_id,
                team_id=team_id,
                channel_id=channel_id,
                can_access=can_access,
                expires_at=utc_now(),
            )
            session.add(cached)
        cached.can_access = can_access
        cached.checked_at = utc_now()
        cached.expires_at = utc_now() + timedelta(seconds=SLACK_VISIBILITY_CACHE_TTL_SECONDS)
