from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select

from src.backend.application.services.auth_service import normalize_email_key
from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import Workspace, WorkspaceMember


def update_workspace_member_connector_manager(
    owner_id: str,
    workspace_id: str,
    email: str,
    connector_manager: bool,
) -> dict:
    email_key = normalize_email_key(email)
    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id.strip())
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        if workspace.owner_user_id != owner_id:
            raise PermissionDeniedError("Workspace owner access required.")
        member = session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.member_email_key == email_key,
            )
        )
        if member is None:
            raise ResourceNotFoundError("Workspace member not found.")
        if member.user_id == workspace.owner_user_id:
            member.connector_manager = True
        else:
            member.connector_manager = bool(connector_manager)
        return public_member(member, owner_id=workspace.owner_user_id)


def user_can_manage_workspace_connectors(user_id: str, user_email: str, workspace_id: str) -> bool:
    email_key = normalize_email_key(user_email)
    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id.strip())
        if workspace is None:
            return False
        if workspace.owner_user_id == user_id:
            return True
        membership = session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id.strip(),
                or_(
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.member_email_key == email_key,
                ),
            )
        )
        return bool(membership and membership.connector_manager)


def public_member(member: WorkspaceMember, owner_id: str) -> dict:
    is_owner = member.user_id == owner_id
    return {
        "email": member.member_email,
        "user_id": member.user_id,
        "added_at": format_datetime(member.added_at),
        "is_owner": is_owner,
        "connector_manager": bool(is_owner or member.connector_manager),
    }


def format_datetime(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
