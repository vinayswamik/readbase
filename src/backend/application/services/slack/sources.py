from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.backend.application.services.workspace_service import user_can_access_workspace
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    OrgSource,
    SlackUserConnection,
    SlackIndexedItem,
    Workspace,
    WorkspaceSlackSource,
    WorkspaceSourceSubscription,
    utc_now,
)

from .auth import get_valid_slack_access_token
from .http import slack_api_request
from .permissions import verify_slack_channel_access
from .search import normalize_search_tokens, score_channel_match, sort_channels, sort_scored_channels
from .serializers import public_channel, public_source, public_team
from .teams import require_linked_slack_team
from .utils import bool_payload, required_payload


def list_visible_slack_channels(
    user_id: str,
    team_id: str,
    query: str = "",
    *,
    match_limit: int = 50,
) -> list[dict]:
    access_token = get_valid_slack_access_token(user_id, team_id)
    team = get_user_team(user_id, team_id)
    tokens = normalize_search_tokens(query)
    channels: list[dict] = []
    scored_channels: list[tuple[int, dict]] = []
    cursor = ""
    for _ in range(5):
        params = {
            "exclude_archived": "true",
            "limit": "200",
            "types": "public_channel,private_channel",
        }
        if cursor:
            params["cursor"] = cursor
        data = slack_api_request("/users.conversations", token=access_token, query=params)
        for channel in data.get("channels", []) if isinstance(data, dict) else []:
            serialized = public_channel(channel, team)
            if not serialized["channel_id"] or not serialized["channel_name"]:
                continue
            if tokens:
                score = score_channel_match(
                    serialized["channel_name"],
                    serialized.get("team_name", ""),
                    tokens,
                )
                if score >= 0:
                    scored_channels.append((score, serialized))
            else:
                channels.append(serialized)
        if tokens and len(scored_channels) >= match_limit:
            break
        cursor = str((data.get("response_metadata") or {}).get("next_cursor") or "") if isinstance(data, dict) else ""
        if not cursor:
            break
    if tokens:
        return sort_scored_channels(scored_channels)[:match_limit]
    return channels


def list_workspace_slack_sources(workspace_id: str, user_id: str) -> list[dict]:
    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        sources = session.scalars(
            select(OrgSource)
            .join(
                WorkspaceSourceSubscription,
                WorkspaceSourceSubscription.source_id == OrgSource.source_id,
            )
            .where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                OrgSource.provider == "slack",
            )
            .order_by(OrgSource.created_at.desc())
        ).all()
        connected_team_ids = {
            row.team_id
            for row in session.scalars(select(SlackUserConnection).where(SlackUserConnection.user_id == user_id)).all()
        }
        sync_owners = {
            row.source_id: row.sync_owner_user_id
            for row in session.scalars(
                select(WorkspaceSlackSource).where(WorkspaceSlackSource.source_id.in_([source.source_id for source in sources]))
            ).all()
        }
        return [
            public_source(
                source,
                workspace_id=normalized_workspace_id,
                sync_owner_user_id=sync_owners.get(source.source_id),
                user_access=(
                    "connected"
                    if str(_parse_metadata(source.metadata_json).get("team_id") or "") in connected_team_ids
                    else "connect_slack"
                ),
            )
            for source in sources
        ]


def add_workspace_slack_source(workspace_id: str, actor_user_id: str, actor_email: str, payload: dict) -> dict:
    require_workspace_access(actor_user_id, actor_email, workspace_id)
    team_id = required_payload(payload, "team_id")
    channel_id = required_payload(payload, "channel_id")
    channel_name = required_payload(payload, "channel_name")
    channel_is_private = bool_payload(payload, "is_private")
    access_token = get_valid_slack_access_token(actor_user_id, team_id)
    verify_slack_channel_access(access_token, channel_id)
    require_linked_slack_team(workspace_id, team_id)

    with session_scope() as session:
        normalized_workspace_id = workspace_id.strip()
        workspace = session.get(Workspace, normalized_workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        org_id = (workspace.organization_id or workspace.workspace_id).strip()
        connection = session.scalar(
            select(SlackUserConnection).where(
                SlackUserConnection.user_id == actor_user_id,
                SlackUserConnection.team_id == team_id,
            )
        )
        if connection is None:
            raise PermissionDeniedError("Connect Slack with access to this workspace before adding the channel.")
        external_key = f"{connection.team_id}:{channel_id}"
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.org_id == org_id,
                OrgSource.provider == "slack",
                OrgSource.external_key == external_key,
            )
        )
        if source is None:
            source = OrgSource(
                source_id=f"slack-{uuid4().hex[:16]}",
                org_id=org_id,
                provider="slack",
                external_key=external_key,
                display_name=f"{connection.team_name} #{channel_name}",
                source_url=None,
                metadata_json=json.dumps(
                    {
                        "team_id": connection.team_id,
                        "team_name": connection.team_name,
                        "team_domain": connection.team_domain,
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                        "channel_is_private": channel_is_private,
                        "last_message_ts": "",
                    },
                    sort_keys=True,
                ),
                added_by_user_id=actor_user_id,
                sync_owner_user_id=actor_user_id,
                next_sync_at=utc_now(),
            )
            session.add(source)
            # Compatibility row: keeps existing indexed-item FK valid while sync stays on org source IDs.
            session.add(
                WorkspaceSlackSource(
                    source_id=source.source_id,
                    workspace_id=normalized_workspace_id,
                    team_id=connection.team_id,
                    team_name=connection.team_name,
                    team_domain=connection.team_domain,
                    channel_id=channel_id,
                    channel_name=channel_name,
                    channel_is_private=channel_is_private,
                    added_by_user_id=actor_user_id,
                    sync_owner_user_id=actor_user_id,
                    next_sync_at=utc_now(),
                )
            )
        subscription = WorkspaceSourceSubscription(
            workspace_id=normalized_workspace_id,
            source_id=source.source_id,
            added_by_user_id=actor_user_id,
        )
        session.add(subscription)
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("Slack channel is already connected to this workspace.") from exc
        return public_source(source, workspace_id=normalized_workspace_id, user_access="connected")


def remove_workspace_slack_source(workspace_id: str, source_id: str, actor_user_id: str, actor_email: str) -> dict:
    require_workspace_access(actor_user_id, actor_email, workspace_id)
    normalized_workspace_id = workspace_id.strip()
    with session_scope() as session:
        source = session.scalar(
            select(OrgSource).where(
                OrgSource.source_id == source_id.strip(),
                OrgSource.provider == "slack",
            )
        )
        subscription = session.scalar(
            select(WorkspaceSourceSubscription).where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                WorkspaceSourceSubscription.source_id == source_id.strip(),
            )
        )
        if source is None or subscription is None:
            raise ResourceNotFoundError("Slack source not found.")
        metadata = _parse_metadata(source.metadata_json)
        team_id = str(metadata.get("team_id") or "")
        channel_id = str(metadata.get("channel_id") or "")
        access_token = get_valid_slack_access_token(actor_user_id, team_id)
        verify_slack_channel_access(access_token, channel_id)
        public = public_source(source, workspace_id=normalized_workspace_id, user_access="unknown")
        session.delete(subscription)
        has_remaining = session.scalar(
            select(WorkspaceSourceSubscription.subscription_id)
            .where(WorkspaceSourceSubscription.source_id == source.source_id)
            .limit(1)
        )
        if has_remaining is None:
            session.execute(delete(SlackIndexedItem).where(SlackIndexedItem.source_id == source.source_id))
            session.execute(delete(WorkspaceSlackSource).where(WorkspaceSlackSource.source_id == source.source_id))
            session.delete(source)
        return public


def get_user_team(user_id: str, team_id: str) -> dict:
    with session_scope() as session:
        connection = session.scalar(
            select(SlackUserConnection).where(
                SlackUserConnection.user_id == user_id,
                SlackUserConnection.team_id == team_id.strip(),
            )
        )
        if connection is None:
            raise PermissionDeniedError("Connect Slack before selecting channels.")
        return public_team(connection)


def require_workspace_access(user_id: str, user_email: str, workspace_id: str) -> None:
    if not user_can_access_workspace(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Workspace access required.")


def _parse_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
