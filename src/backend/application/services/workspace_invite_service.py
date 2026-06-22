from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.auth_service import AuthUser, normalize_email_key
from src.backend.application.services.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import HierarchyNode, User, Workspace, WorkspaceInvite, WorkspaceMember

LINK_INVITE_EMAIL_LABEL = "Anyone with the link"
LINK_INVITE_NAME = "Open invite"
INVITE_TTL_DAYS = 7


def list_invites_for_user(user_id: str, user_email: str) -> dict:
    email_key = normalize_email_key(user_email)
    with session_scope() as session:
        received = session.scalars(
            select(WorkspaceInvite)
            .where(
                WorkspaceInvite.invitee_email_key == email_key,
                WorkspaceInvite.status == "pending",
                WorkspaceInvite.join_token.is_(None),
            )
            .order_by(WorkspaceInvite.created_at.desc())
        ).all()
        sent = session.scalars(
            select(WorkspaceInvite)
            .where(
                WorkspaceInvite.invitor_user_id == user_id,
                WorkspaceInvite.status == "pending",
            )
            .order_by(WorkspaceInvite.created_at.desc())
        ).all()
        workspace_names = _workspace_names_by_id(
            session,
            {invite.workspace_id for invite in (*received, *sent)},
        )
        return {
            "received": [
                _public_invite(invite, workspace_names.get(invite.workspace_id, ""), "received")
                for invite in received
                if not _invite_is_expired(invite)
            ],
            "sent": [
                _public_invite(invite, workspace_names.get(invite.workspace_id, ""), "sent")
                for invite in sent
                if not _invite_is_expired(invite)
            ],
        }


def create_workspace_invite(
    workspace_id: str,
    invitor: AuthUser,
    *,
    invitee_email: str,
    invitor_designation: str,
    relation: str,
    reason: str,
    node_display_name: str,
    parent_node_id: str | None = None,
    node_x: float = 0,
    node_y: float = 0,
) -> dict:
    with session_scope() as session:
        invite, workspace_name = prepare_workspace_invite(
            session,
            workspace_id,
            invitor,
            invitee_email=invitee_email,
            invitor_designation=invitor_designation,
            relation=relation,
            reason=reason,
            node_display_name=node_display_name,
            parent_node_id=parent_node_id,
            node_x=node_x,
            node_y=node_y,
        )
        return _public_invite(invite, workspace_name, "sent")


def prepare_link_workspace_invite(
    session,
    workspace_id: str,
    invitor: AuthUser,
    *,
    invitor_designation: str,
    relation: str,
    reason: str,
    node_display_name: str,
    parent_node_id: str | None = None,
    node_x: float = 0,
    node_y: float = 0,
) -> tuple[WorkspaceInvite, str, str]:
    normalized_relation = _normalize_short_text(relation, "Relation")
    normalized_reason = _normalize_long_text(reason, "Reason")
    normalized_designation = _normalize_short_text(
        invitor_designation,
        "Your designation",
        required=False,
    )
    normalized_node_name = _normalize_short_text(node_display_name, "Display name")

    membership = session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            or_(
                WorkspaceMember.user_id == invitor.user_id,
                WorkspaceMember.member_email_key == normalize_email_key(invitor.email),
            ),
        )
    )
    if membership is None:
        raise ValidationError("Workspace access required.")

    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise ValidationError("Workspace not found.")

    join_token_raw = _new_join_token()
    join_token_hash = _hash_join_token(join_token_raw)
    invite = WorkspaceInvite(
        invite_id=_new_invite_id(),
        workspace_id=workspace_id,
        invitee_email=LINK_INVITE_EMAIL_LABEL,
        invitee_email_key=_link_invite_email_key(join_token_hash),
        invitee_name=LINK_INVITE_NAME,
        invitee_user_id=None,
        invitor_user_id=invitor.user_id,
        invitor_name=invitor.name,
        invitor_designation=normalized_designation,
        relation=normalized_relation,
        reason=normalized_reason,
        node_display_name=normalized_node_name,
        parent_node_id=parent_node_id or None,
        node_x=float(node_x),
        node_y=float(node_y),
        status="pending",
        join_token=join_token_hash,
        expires_at=_invite_expires_at(),
    )
    session.add(invite)
    session.flush()
    return invite, workspace.name, join_token_raw


def get_link_invite_preview(user: AuthUser, join_token: str) -> dict:
    normalized_token = join_token.strip()
    if not normalized_token:
        raise ResourceNotFoundError("Invite link is invalid or expired.")
    with session_scope() as session:
        invite = _find_invite_by_join_token(session, normalized_token)
        if invite is None or invite.status != "pending":
            raise ResourceNotFoundError("Invite link is invalid or expired.")
        _ensure_invite_not_expired(invite)
        workspace = session.get(Workspace, invite.workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Invite link is invalid or expired.")
        if workspace.owner_user_id == user.user_id:
            raise ValidationError("You already manage this workspace.")
        existing_node = session.scalar(
            select(HierarchyNode.node_id).where(
                HierarchyNode.workspace_id == invite.workspace_id,
                HierarchyNode.assigned_user_id == user.user_id,
            )
        )
        if existing_node is not None:
            raise ValidationError("You already belong to this workspace.")
        workspace_name = workspace.name
        return _public_invite(invite, workspace_name, "received")


def prepare_workspace_invite(
    session,
    workspace_id: str,
    invitor: AuthUser,
    *,
    invitee_email: str,
    invitor_designation: str,
    relation: str,
    reason: str,
    node_display_name: str,
    parent_node_id: str | None = None,
    node_x: float = 0,
    node_y: float = 0,
) -> tuple[WorkspaceInvite, str]:
    normalized_email = _normalize_email(invitee_email)
    email_key = normalize_email_key(normalized_email)
    normalized_relation = _normalize_short_text(relation, "Relation")
    normalized_reason = _normalize_long_text(reason, "Reason")
    normalized_designation = _normalize_short_text(
        invitor_designation,
        "Your designation",
        required=False,
    )
    normalized_node_name = _normalize_short_text(node_display_name, "Display name")

    membership = session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            or_(
                WorkspaceMember.user_id == invitor.user_id,
                WorkspaceMember.member_email_key == normalize_email_key(invitor.email),
            ),
        )
    )
    if membership is None:
        raise ValidationError("Workspace access required.")

    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise ValidationError("Workspace not found.")

    invitee_user = session.scalar(select(User).where(User.email_key == email_key))
    invitee_name = invitee_user.name if invitee_user else _name_from_email(normalized_email)

    invite = WorkspaceInvite(
        invite_id=_new_invite_id(),
        workspace_id=workspace_id,
        invitee_email=normalized_email,
        invitee_email_key=email_key,
        invitee_name=invitee_name,
        invitee_user_id=invitee_user.user_id if invitee_user else None,
        invitor_user_id=invitor.user_id,
        invitor_name=invitor.name,
        invitor_designation=normalized_designation,
        relation=normalized_relation,
        reason=normalized_reason,
        node_display_name=normalized_node_name,
        parent_node_id=parent_node_id or None,
        node_x=float(node_x),
        node_y=float(node_y),
        status="pending",
        expires_at=_invite_expires_at(),
    )
    session.add(invite)
    session.flush()
    return invite, workspace.name


def sync_pending_invites_for_user(user_id: str, email: str) -> None:
    email_key = normalize_email_key(email)
    with session_scope() as session:
        invites = session.scalars(
            select(WorkspaceInvite).where(
                WorkspaceInvite.invitee_email_key == email_key,
                WorkspaceInvite.status == "pending",
                WorkspaceInvite.node_id.is_(None),
                WorkspaceInvite.join_token.is_(None),
            )
        ).all()
        if not invites:
            return

        invitee_name = session.scalar(select(User.name).where(User.user_id == user_id))
        for invite in invites:
            invite.invitee_user_id = user_id
            if invitee_name:
                invite.invitee_name = invitee_name


def fulfill_pending_invites_for_user(user_id: str, email: str) -> None:
    """Legacy alias kept for tests; invites now require explicit acceptance."""
    sync_pending_invites_for_user(user_id, email)


def accept_workspace_invite(user: AuthUser, invite_id: str) -> dict:
    from src.backend.application.services.hierarchy_graph_service import (
        create_node_from_invite,
    )

    email_key = normalize_email_key(user.email)
    normalized_invite_id = invite_id.strip()
    workspace_name = ""
    with session_scope() as session:
        invite = session.get(WorkspaceInvite, normalized_invite_id)
        if invite is None:
            raise ResourceNotFoundError("Invite not found.")
        if invite.status != "pending":
            raise ValidationError("This invite is no longer pending.")
        _ensure_invite_not_expired(invite)
        if invite.node_id is not None:
            raise ValidationError("This invite has already been fulfilled.")

        workspace = session.get(Workspace, invite.workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        workspace_name = workspace.name

        if _is_link_invite(invite):
            if workspace.owner_user_id == user.user_id:
                raise ValidationError("You already manage this workspace.")
            existing_node = session.scalar(
                select(HierarchyNode.node_id).where(
                    HierarchyNode.workspace_id == invite.workspace_id,
                    HierarchyNode.assigned_user_id == user.user_id,
                )
            )
            if existing_node is not None:
                raise ValidationError("You already belong to this workspace.")
            _ensure_invitee_membership(session, invite, user)
            invite.invitee_email = user.email
            invite.invitee_email_key = email_key
            invite.invitee_user_id = user.user_id
            invite.invitee_name = user.name
        elif invite.invitee_email_key != email_key:
            raise PermissionDeniedError("This invite is not for your account.")
        else:
            _ensure_invitee_membership(session, invite, user)
            invite.invitee_user_id = user.user_id
            invite.invitee_name = user.name
        accepted_invite = _public_invite(invite, workspace_name, "received")

    create_node_from_invite(normalized_invite_id, user.user_id)

    return {
        **accepted_invite,
        "status": "active",
        "can_accept": False,
        "can_reject": False,
        "can_revert": False,
    }


def reject_workspace_invite(user: AuthUser, invite_id: str) -> dict:
    email_key = normalize_email_key(user.email)
    normalized_invite_id = invite_id.strip()
    with session_scope() as session:
        invite = session.get(WorkspaceInvite, normalized_invite_id)
        if invite is None:
            raise ResourceNotFoundError("Invite not found.")
        if _is_link_invite(invite):
            raise ValidationError("Use the invite link to accept this invitation.")
        if invite.invitee_email_key != email_key:
            raise PermissionDeniedError("This invite is not for your account.")
        if invite.status != "pending":
            raise ValidationError("This invite is no longer pending.")

        workspace = session.get(Workspace, invite.workspace_id)
        workspace_name = workspace.name if workspace is not None else ""
        invite.status = "rejected"

        if workspace is not None:
            _remove_provisional_membership_for_invite(session, invite, workspace)

        return _public_invite(invite, workspace_name, "received")


def revert_workspace_invite(user: AuthUser, invite_id: str) -> dict:
    normalized_invite_id = invite_id.strip()
    with session_scope() as session:
        invite = session.get(WorkspaceInvite, normalized_invite_id)
        if invite is None:
            raise ResourceNotFoundError("Invite not found.")
        if invite.invitor_user_id != user.user_id:
            raise PermissionDeniedError("Only the person who sent this invite can revert it.")
        if invite.status != "pending":
            raise ValidationError("This invite is no longer pending.")
        if invite.node_id is not None:
            raise ValidationError("This invite has already been accepted.")

        workspace = session.get(Workspace, invite.workspace_id)
        workspace_name = workspace.name if workspace is not None else ""
        if _is_link_invite(invite):
            public = _public_invite(invite, workspace_name, "sent")
            session.delete(invite)
            return public

        invite.status = "reverted"
        if workspace is not None:
            _remove_provisional_membership_for_invite(session, invite, workspace)

        return _public_invite(invite, workspace_name, "sent")


def _remove_provisional_membership_for_invite(
    session,
    invite: WorkspaceInvite,
    workspace: Workspace,
) -> None:
    if invite.node_id is not None:
        return

    member = session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == invite.workspace_id,
            WorkspaceMember.member_email_key == invite.invitee_email_key,
        )
    )
    if member is None or member.user_id == workspace.owner_user_id:
        return

    assigned_user_id = invite.invitee_user_id or member.user_id
    if assigned_user_id:
        has_node = session.scalar(
            select(HierarchyNode.node_id).where(
                HierarchyNode.workspace_id == invite.workspace_id,
                HierarchyNode.assigned_user_id == assigned_user_id,
            )
        )
        if has_node is not None:
            return

    session.delete(member)


def mark_invite_active(session, invite: WorkspaceInvite, node_id: str) -> None:
    _ = node_id
    session.delete(invite)


def _invite_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS)


def _ensure_invite_not_expired(invite: WorkspaceInvite) -> None:
    if invite.expires_at is None:
        return
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise ResourceNotFoundError("Invite link is invalid or expired.")


def _workspace_names_by_id(session, workspace_ids: set[str]) -> dict[str, str]:
    if not workspace_ids:
        return {}
    rows = session.execute(
        select(Workspace.workspace_id, Workspace.name).where(
            Workspace.workspace_id.in_(workspace_ids)
        )
    ).all()
    return {workspace_id: name for workspace_id, name in rows}


def _public_invite(
    invite: WorkspaceInvite,
    workspace_name: str,
    direction: str,
    *,
    reveal_join_token: str | None = None,
) -> dict:
    is_pending = invite.status == "pending"
    is_link = _is_link_invite(invite)
    join_token = reveal_join_token if reveal_join_token else None
    return {
        "invite_id": invite.invite_id,
        "workspace_id": invite.workspace_id,
        "workspace_name": workspace_name,
        "direction": direction,
        "invite_method": "link" if is_link else "email",
        "invitee_email": invite.invitee_email,
        "invitee_name": invite.invitee_name,
        "invitee_user_id": invite.invitee_user_id,
        "invitor_user_id": invite.invitor_user_id,
        "invitor_name": invite.invitor_name,
        "invitor_designation": invite.invitor_designation,
        "relation": invite.relation,
        "reason": invite.reason,
        "node_display_name": invite.node_display_name,
        "node_id": invite.node_id,
        "status": invite.status,
        "join_token": join_token,
        "join_path": _join_path_for_token(join_token),
        "can_accept": direction == "received" and is_pending,
        "can_reject": direction == "received" and is_pending and not is_link,
        "can_revert": direction == "sent" and is_pending,
        "created_at": _format_datetime(invite.created_at),
    }


def _is_link_invite(invite: WorkspaceInvite) -> bool:
    return bool(invite.join_token)


def _link_invite_email_key(join_token: str) -> str:
    return f"link:{join_token}"


def _hash_join_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _find_invite_by_join_token(session, token: str) -> WorkspaceInvite | None:
    token_hash = _hash_join_token(token)
    return session.scalar(select(WorkspaceInvite).where(WorkspaceInvite.join_token == token_hash))


def _invite_is_expired(invite: WorkspaceInvite) -> bool:
    if invite.expires_at is None:
        return False
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def _new_join_token() -> str:
    return secrets.token_urlsafe(18)


def _join_path_for_token(join_token: str | None) -> str | None:
    if not join_token:
        return None
    return f"/?join={join_token}"


def _ensure_invitee_membership(session, invite: WorkspaceInvite, user: AuthUser) -> None:
    email_key = normalize_email_key(user.email)
    member = session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == invite.workspace_id,
            WorkspaceMember.member_email_key == email_key,
        )
    )
    if member is None:
        member = WorkspaceMember(
            workspace_id=invite.workspace_id,
            user_id=user.user_id,
            member_email=user.email.strip(),
            member_email_key=email_key,
            added_by_user_id=invite.invitor_user_id,
        )
        session.add(member)
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("Workspace member already exists.") from exc
    else:
        member.user_id = user.user_id


def _normalize_email(email: str) -> str:
    normalized = email.strip()
    if not normalized or "@" not in normalized:
        raise ValidationError("A valid email address is required.")
    if len(normalized) > 320:
        raise ValidationError("Email address is too long.")
    return normalized


def _normalize_short_text(value: str, label: str, *, required: bool = True) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        if required:
            raise ValidationError(f"{label} is required.")
        return ""
    if len(normalized) > 120:
        raise ValidationError(f"{label} must be 120 characters or fewer.")
    return normalized


def _normalize_long_text(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{label} is required.")
    if len(normalized) > 2000:
        raise ValidationError(f"{label} must be 2000 characters or fewer.")
    return normalized


def _name_from_email(email: str) -> str:
    local = email.split("@", 1)[0].strip()
    return local.replace(".", " ").replace("_", " ").title() or email


def _new_invite_id() -> str:
    return f"invite-{uuid4().hex[:16]}"


def _format_datetime(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
