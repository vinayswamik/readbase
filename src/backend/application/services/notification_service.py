from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import User, UserNotification, Workspace, WorkspaceMember


def list_notifications(user_id: str) -> dict:
    with session_scope() as session:
        notifications = session.scalars(
            select(UserNotification)
            .where(UserNotification.recipient_user_id == user_id)
            .order_by(UserNotification.created_at.desc())
        ).all()
        return {
            "notifications": [_public_notification(notification) for notification in notifications]
        }


def create_workspace_member_left_notifications(
    session,
    *,
    workspace: Workspace,
    actor_user_id: str,
) -> None:
    actor = session.get(User, actor_user_id)
    actor_name = str(actor.name).strip() if actor and str(actor.name).strip() else "A teammate"

    recipient_ids: set[str] = {workspace.owner_user_id}
    for member in session.scalars(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.workspace_id)
    ).all():
        if member.user_id:
            recipient_ids.add(member.user_id)
    recipient_ids.discard(actor_user_id)

    created_at = datetime.now(timezone.utc)
    for recipient_id in recipient_ids:
        session.add(
            UserNotification(
                notification_id=str(uuid4()),
                recipient_user_id=recipient_id,
                type="workspace_member_left",
                workspace_id=workspace.workspace_id,
                workspace_name=workspace.name,
                actor_user_id=actor_user_id,
                actor_name=actor_name,
                read=False,
                created_at=created_at,
            )
        )


def _public_notification(notification: UserNotification) -> dict:
    return {
        "notification_id": notification.notification_id,
        "type": notification.type,
        "title": "Member left workspace",
        "body": f"{notification.actor_name} left {notification.workspace_name}.",
        "workspace_id": notification.workspace_id,
        "workspace_name": notification.workspace_name,
        "actor_user_id": notification.actor_user_id,
        "actor_name": notification.actor_name,
        "read": notification.read,
        "created_at": _format_datetime(notification.created_at),
    }


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
