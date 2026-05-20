from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.backend.application.services.workspace_service import user_can_access_workspace, user_can_manage_workspace_connectors
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import SlackUserConnection, Workspace, WorkspaceSlackSource, utc_now

from .auth import get_valid_slack_access_token
from .http import slack_api_request
from .permissions import verify_slack_channel_access
from .serializers import public_channel, public_source, public_team
from .utils import bool_payload, optional_str, required_payload


def list_visible_slack_channels(user_id: str, team_id: str, query: str = "") -> list[dict]:
    access_token = get_valid_slack_access_token(user_id, team_id)
    team = get_user_team(user_id, team_id)
    normalized_query = query.strip().lower()
    channels: list[dict] = []
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
            if normalized_query and normalized_query not in serialized["channel_name"].lower():
                continue
            channels.append(serialized)
        cursor = str((data.get("response_metadata") or {}).get("next_cursor") or "") if isinstance(data, dict) else ""
        if not cursor:
            break
    return channels


def list_workspace_slack_sources(workspace_id: str, user_id: str) -> list[dict]:
    with session_scope() as session:
        sources = session.scalars(
            select(WorkspaceSlackSource)
            .where(WorkspaceSlackSource.workspace_id == workspace_id.strip())
            .order_by(WorkspaceSlackSource.created_at.desc())
        ).all()
        connected_team_ids = {
            row.team_id
            for row in session.scalars(select(SlackUserConnection).where(SlackUserConnection.user_id == user_id)).all()
        }
        return [
            public_source(source, user_access=("connected" if source.team_id in connected_team_ids else "connect_slack"))
            for source in sources
        ]


def add_workspace_slack_source(workspace_id: str, actor_user_id: str, actor_email: str, payload: dict) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    team_id = required_payload(payload, "team_id")
    channel_id = required_payload(payload, "channel_id")
    channel_name = required_payload(payload, "channel_name")
    channel_is_private = bool_payload(payload, "is_private")
    access_token = get_valid_slack_access_token(actor_user_id, team_id)
    verify_slack_channel_access(access_token, channel_id)

    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id.strip())
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        connection = session.scalar(
            select(SlackUserConnection).where(
                SlackUserConnection.user_id == actor_user_id,
                SlackUserConnection.team_id == team_id,
            )
        )
        if connection is None:
            raise PermissionDeniedError("Connect Slack with access to this workspace before adding the channel.")
        source = WorkspaceSlackSource(
            source_id=f"slack-{uuid4().hex[:16]}",
            workspace_id=workspace.workspace_id,
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
        session.add(source)
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("Slack channel is already connected to this workspace.") from exc
        return public_source(source, user_access="connected")


def remove_workspace_slack_source(workspace_id: str, source_id: str, actor_user_id: str, actor_email: str) -> dict:
    require_connector_manager(actor_user_id, actor_email, workspace_id)
    with session_scope() as session:
        source = session.get(WorkspaceSlackSource, source_id.strip())
        if source is None or source.workspace_id != workspace_id.strip():
            raise ResourceNotFoundError("Slack source not found.")
        public = public_source(source, user_access="unknown")
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


def require_connector_manager(user_id: str, user_email: str, workspace_id: str) -> None:
    if not user_can_access_workspace(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Workspace access required.")
    if not user_can_manage_workspace_connectors(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Connector manager access required.")
