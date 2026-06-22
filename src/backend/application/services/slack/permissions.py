from __future__ import annotations
from datetime import timedelta

from sqlalchemy import select, tuple_

from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    OrgSource,
    SlackUserConnection,
    SlackVisibilityCache,
    WorkspaceSlackAccessCache,
    WorkspaceSourceSubscription,
    utc_now,
)

from .auth import get_valid_slack_access_token
from .constants import SLACK_VISIBILITY_CACHE_TTL_SECONDS, SLACK_WORKSPACE_ACCESS_CACHE_TTL_SECONDS
from .http import slack_api_request
from .utils import as_utc


def filter_slack_matches_for_user(
    user_id: str,
    matches: list[dict],
    workspace_id: str | None = None,
) -> list[dict]:
    channel_keys = {
        (str(match.get("team_id") or ""), str(match.get("channel_id") or ""))
        for match in matches
        if match.get("source_type") == "slack"
    }
    channel_keys.discard(("", ""))
    access_by_channel = build_slack_access_map(user_id, channel_keys, workspace_id=workspace_id)

    permitted: list[dict] = []
    for match in matches:
        if match.get("source_type") != "slack":
            permitted.append(match)
            continue
        team_id = str(match.get("team_id") or "")
        channel_id = str(match.get("channel_id") or "")
        if not team_id or not channel_id:
            continue
        key = (team_id, channel_id)
        if access_by_channel.get(key):
            permitted.append(match)
    return permitted


def build_slack_access_map(
    user_id: str,
    channel_keys: set[tuple[str, str]],
    workspace_id: str | None = None,
) -> dict[tuple[str, str], bool]:
    if not channel_keys:
        return {}

    scoped_keys = resolve_workspace_channel_keys(channel_keys, workspace_id=workspace_id)
    if not scoped_keys:
        return {}

    access_by_channel: dict[tuple[str, str], bool] = {}
    unresolved = set(scoped_keys)
    workspace_cache = read_workspace_access_cache_map(user_id, unresolved, workspace_id=workspace_id)
    access_by_channel.update(workspace_cache)
    unresolved -= set(workspace_cache.keys())

    cached = read_visibility_cache_map(user_id, unresolved)
    access_by_channel.update(cached)
    unresolved -= set(cached.keys())

    if not unresolved:
        return access_by_channel

    connected_teams = list_connected_team_ids(user_id)
    for team_id, channel_id in unresolved:
        if team_id not in connected_teams:
            access_by_channel[(team_id, channel_id)] = False
            continue
        access_by_channel[(team_id, channel_id)] = can_user_access_slack_channel(user_id, team_id, channel_id)
    write_workspace_access_cache_map(user_id, access_by_channel, workspace_id=workspace_id)
    return access_by_channel


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


def read_visibility_cache_map(
    user_id: str,
    channel_keys: set[tuple[str, str]],
) -> dict[tuple[str, str], bool]:
    if not channel_keys:
        return {}
    channel_key_list = list(channel_keys)
    now = utc_now()
    with session_scope() as session:
        rows = session.scalars(
            select(SlackVisibilityCache).where(
                SlackVisibilityCache.user_id == user_id,
                tuple_(SlackVisibilityCache.team_id, SlackVisibilityCache.channel_id).in_(channel_key_list),
            )
        ).all()
    return {
        (row.team_id, row.channel_id): bool(row.can_access)
        for row in rows
        if as_utc(row.expires_at) > now
    }


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


def resolve_workspace_channel_keys(
    channel_keys: set[tuple[str, str]],
    workspace_id: str | None = None,
) -> set[tuple[str, str]]:
    if not workspace_id:
        return set(channel_keys)
    normalized_workspace_id = workspace_id.strip()
    if not normalized_workspace_id:
        return set(channel_keys)
    with session_scope() as session:
        external_keys = session.scalars(
            select(OrgSource.external_key)
            .join(
                WorkspaceSourceSubscription,
                WorkspaceSourceSubscription.source_id == OrgSource.source_id,
            )
            .where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                OrgSource.provider == "slack",
            )
        ).all()
        workspace_channel_keys = set()
        for external_key in external_keys:
            team_id, _, channel_id = str(external_key).partition(":")
            if team_id and channel_id:
                workspace_channel_keys.add((team_id, channel_id))
    return channel_keys & workspace_channel_keys


def list_connected_team_ids(user_id: str) -> set[str]:
    with session_scope() as session:
        return {
            row.team_id
            for row in session.scalars(select(SlackUserConnection).where(SlackUserConnection.user_id == user_id)).all()
        }


def read_workspace_access_cache_map(
    user_id: str,
    channel_keys: set[tuple[str, str]],
    workspace_id: str | None = None,
) -> dict[tuple[str, str], bool]:
    normalized_workspace_id = (workspace_id or "").strip()
    if not normalized_workspace_id or not channel_keys:
        return {}
    channel_key_list = list(channel_keys)
    now = utc_now()
    with session_scope() as session:
        rows = session.scalars(
            select(WorkspaceSlackAccessCache).where(
                WorkspaceSlackAccessCache.workspace_id == normalized_workspace_id,
                WorkspaceSlackAccessCache.user_id == user_id,
                tuple_(WorkspaceSlackAccessCache.team_id, WorkspaceSlackAccessCache.channel_id).in_(channel_key_list),
            )
        ).all()
    return {
        (row.team_id, row.channel_id): bool(row.can_access)
        for row in rows
        if as_utc(row.expires_at) > now
    }


def write_workspace_access_cache_map(
    user_id: str,
    access_by_channel: dict[tuple[str, str], bool],
    workspace_id: str | None = None,
) -> None:
    normalized_workspace_id = (workspace_id or "").strip()
    if not normalized_workspace_id or not access_by_channel:
        return
    now = utc_now()
    expires_at = now + timedelta(seconds=SLACK_WORKSPACE_ACCESS_CACHE_TTL_SECONDS)
    with session_scope() as session:
        channel_keys = list(access_by_channel.keys())
        existing_rows = {
            (row.team_id, row.channel_id): row
            for row in session.scalars(
                select(WorkspaceSlackAccessCache).where(
                    WorkspaceSlackAccessCache.workspace_id == normalized_workspace_id,
                    WorkspaceSlackAccessCache.user_id == user_id,
                    tuple_(WorkspaceSlackAccessCache.team_id, WorkspaceSlackAccessCache.channel_id).in_(channel_keys),
                )
            ).all()
        }
        for (team_id, channel_id), can_access in access_by_channel.items():
            row = existing_rows.get((team_id, channel_id))
            if row is None:
                row = WorkspaceSlackAccessCache(
                    workspace_id=normalized_workspace_id,
                    user_id=user_id,
                    team_id=team_id,
                    channel_id=channel_id,
                    can_access=can_access,
                    checked_at=now,
                    expires_at=expires_at,
                )
                session.add(row)
                continue
            row.can_access = can_access
            row.checked_at = now
            row.expires_at = expires_at
