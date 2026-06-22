from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.backend.application.services.workspace_service import user_can_access_workspace
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    OrgSource,
    SlackIndexedItem,
    SlackUserConnection,
    Workspace,
    WorkspaceSlackSource,
    WorkspaceSlackTeam,
    WorkspaceSourceSubscription,
    utc_now,
)

from .auth import get_valid_slack_access_token
from .search import normalize_search_tokens, score_channel_match, sort_channels, sort_scored_channels
from .serializers import public_team_link
from .sync import rebuild_workspace_slack_index


def require_workspace_access(user_id: str, user_email: str, workspace_id: str) -> None:
    if not user_can_access_workspace(user_id, user_email, workspace_id):
        raise PermissionDeniedError("Workspace access required.")


def list_workspace_slack_teams(workspace_id: str, user_id: str) -> list[dict]:
    normalized_workspace_id = workspace_id.strip()
    with session_scope() as session:
        linked_teams = session.scalars(
            select(WorkspaceSlackTeam)
            .where(WorkspaceSlackTeam.workspace_id == normalized_workspace_id)
            .order_by(WorkspaceSlackTeam.team_name.asc())
        ).all()
        oauth_team_ids = {
            row.team_id
            for row in session.scalars(
                select(SlackUserConnection).where(SlackUserConnection.user_id == user_id)
            ).all()
        }
        return [
            public_team_link(team, user_oauth_connected=team.team_id in oauth_team_ids)
            for team in linked_teams
        ]


def workspace_has_linked_slack_teams(workspace_id: str) -> bool:
    normalized_workspace_id = workspace_id.strip()
    with session_scope() as session:
        linked = session.scalar(
            select(WorkspaceSlackTeam.team_link_id)
            .where(WorkspaceSlackTeam.workspace_id == normalized_workspace_id)
            .limit(1)
        )
        return linked is not None


def workspace_slack_team_is_linked(workspace_id: str, team_id: str) -> bool:
    normalized_workspace_id = workspace_id.strip()
    normalized_team_id = team_id.strip()
    if not normalized_workspace_id or not normalized_team_id:
        return False
    with session_scope() as session:
        linked = session.scalar(
            select(WorkspaceSlackTeam.team_link_id).where(
                WorkspaceSlackTeam.workspace_id == normalized_workspace_id,
                WorkspaceSlackTeam.team_id == normalized_team_id,
            )
        )
        return linked is not None


def link_workspace_slack_team(
    workspace_id: str,
    actor_user_id: str,
    team_id: str,
    *,
    team_name: str | None = None,
    team_domain: str | None = None,
) -> dict:
    normalized_workspace_id = workspace_id.strip()
    normalized_team_id = team_id.strip()
    if not normalized_team_id:
        raise ValidationError("Slack team_id is required.")

    with session_scope() as session:
        workspace = session.get(Workspace, normalized_workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        connection = session.scalar(
            select(SlackUserConnection).where(
                SlackUserConnection.user_id == actor_user_id,
                SlackUserConnection.team_id == normalized_team_id,
            )
        )
        if connection is None:
            raise PermissionDeniedError("Connect Slack with access to this workspace before linking it here.")

        resolved_name = team_name or connection.team_name
        resolved_domain = team_domain if team_domain is not None else connection.team_domain
        existing = session.scalar(
            select(WorkspaceSlackTeam).where(
                WorkspaceSlackTeam.workspace_id == normalized_workspace_id,
                WorkspaceSlackTeam.team_id == normalized_team_id,
            )
        )
        if existing is not None:
            raise ValidationError("This Slack workspace is already connected to this Readbase workspace.")

        now = utc_now()
        existing = WorkspaceSlackTeam(
            workspace_id=normalized_workspace_id,
            team_id=normalized_team_id,
            team_name=resolved_name,
            team_domain=resolved_domain,
            linked_by_user_id=actor_user_id,
            linked_at=now,
            updated_at=now,
        )
        session.add(existing)
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("This Slack workspace is already connected to this Readbase workspace.") from exc
        oauth_connected = True
        return public_team_link(existing, user_oauth_connected=oauth_connected)


def link_workspace_slack_team_for_user(
    workspace_id: str,
    actor_user_id: str,
    actor_email: str,
    team_id: str,
) -> dict:
    require_workspace_access(actor_user_id, actor_email, workspace_id)
    return link_workspace_slack_team(workspace_id, actor_user_id, team_id)


def unlink_workspace_slack_team(
    workspace_id: str,
    actor_user_id: str,
    actor_email: str,
    team_id: str,
) -> dict:
    require_workspace_access(actor_user_id, actor_email, workspace_id)
    normalized_workspace_id = workspace_id.strip()
    normalized_team_id = team_id.strip()
    with session_scope() as session:
        linked = session.scalar(
            select(WorkspaceSlackTeam).where(
                WorkspaceSlackTeam.workspace_id == normalized_workspace_id,
                WorkspaceSlackTeam.team_id == normalized_team_id,
            )
        )
        if linked is None:
            raise ResourceNotFoundError("Slack workspace link not found.")
        public = public_team_link(linked, user_oauth_connected=False)
        source_ids = session.scalars(
            select(WorkspaceSourceSubscription.source_id)
            .join(OrgSource, OrgSource.source_id == WorkspaceSourceSubscription.source_id)
            .where(
                WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                OrgSource.provider == "slack",
                OrgSource.external_key.like(f"{normalized_team_id}:%"),
            )
        ).all()
        if source_ids:
            session.execute(
                delete(WorkspaceSourceSubscription).where(
                    WorkspaceSourceSubscription.workspace_id == normalized_workspace_id,
                    WorkspaceSourceSubscription.source_id.in_(source_ids),
                )
            )
            remaining_source_ids = {
                row
                for row in session.scalars(
                    select(WorkspaceSourceSubscription.source_id).where(
                        WorkspaceSourceSubscription.source_id.in_(source_ids)
                    )
                ).all()
            }
            purge_source_ids = [source_id for source_id in source_ids if source_id not in remaining_source_ids]
            if purge_source_ids:
                session.execute(delete(SlackIndexedItem).where(SlackIndexedItem.source_id.in_(purge_source_ids)))
                session.execute(delete(WorkspaceSlackSource).where(WorkspaceSlackSource.source_id.in_(purge_source_ids)))
                session.execute(delete(OrgSource).where(OrgSource.source_id.in_(purge_source_ids)))
        session.delete(linked)
    rebuild_workspace_slack_index(normalized_workspace_id)
    return public


def list_linked_team_ids(workspace_id: str) -> list[str]:
    normalized_workspace_id = workspace_id.strip()
    with session_scope() as session:
        return [
            row.team_id
            for row in session.scalars(
                select(WorkspaceSlackTeam).where(WorkspaceSlackTeam.workspace_id == normalized_workspace_id)
            ).all()
        ]


def require_linked_slack_team(workspace_id: str, team_id: str) -> None:
    normalized_workspace_id = workspace_id.strip()
    normalized_team_id = team_id.strip()
    with session_scope() as session:
        linked = session.scalar(
            select(WorkspaceSlackTeam.team_link_id).where(
                WorkspaceSlackTeam.workspace_id == normalized_workspace_id,
                WorkspaceSlackTeam.team_id == normalized_team_id,
            )
        )
        if linked is None:
            raise PermissionDeniedError("Link this Slack workspace to the Readbase workspace before adding channels.")


def list_workspace_slack_channels(workspace_id: str, user_id: str, query: str = "") -> list[dict]:
    from .sources import list_visible_slack_channels

    normalized_query = query.strip()
    tokens = normalize_search_tokens(normalized_query)
    linked_team_ids = list_linked_team_ids(workspace_id)
    if not linked_team_ids:
        return []

    channels_by_key: dict[tuple[str, str], dict] = {}
    for team_id in linked_team_ids:
        try:
            get_valid_slack_access_token(user_id, team_id)
        except PermissionDeniedError:
            continue
        for channel in list_visible_slack_channels(user_id, team_id, query=normalized_query):
            channels_by_key[(channel["team_id"], channel["channel_id"])] = channel

    channels = list(channels_by_key.values())
    if tokens:
        scored = [
            (
                score_channel_match(channel.get("channel_name", ""), channel.get("team_name", ""), tokens),
                channel,
            )
            for channel in channels
        ]
        scored = [item for item in scored if item[0] >= 0]
        channels = sort_scored_channels(scored)
        return channels[:50]

    channels = sort_channels(channels)
    return channels[:500]
