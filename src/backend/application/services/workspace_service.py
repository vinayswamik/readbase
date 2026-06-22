from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.auth_service import normalize_email_key
from src.backend.application.services.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from src.backend.application.services.workspace_connector_permissions import (
    update_workspace_member_connector_manager,
    user_can_manage_workspace_connectors,
)
from src.backend.config.settings import CLI_STATE_FILE, DATA_DIR
from src.backend.infrastructure.storage.resolver import resolve_storage_context
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.ingestion.repo_manager import list_indexes
from src.backend.infrastructure.models import (
    HierarchyConnection,
    HierarchyNode,
    User,
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
)
from src.backend.infrastructure.retrieval.retriever import delete_index

CLI_OWNER_ID = "local-cli"


def list_workspaces(
    user_id: str,
    user_email: str | None = None,
) -> list[dict]:
    email_key = _email_key_for_user(user_id, user_email)
    with session_scope() as session:
        workspaces = list(
            session.scalars(
                select(Workspace)
                .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.workspace_id)
                .where(
                    or_(
                        WorkspaceMember.user_id == user_id,
                        WorkspaceMember.member_email_key == email_key,
                    )
                )
                .order_by(Workspace.created_at.desc())
            )
            .unique()
            .all()
        )
        joined_workspace_ids = {
            workspace.workspace_id
            for workspace in workspaces
            if workspace.owner_user_id != user_id
        }
        workspace_ids_with_nodes: set[str] = set()
        if joined_workspace_ids:
            workspace_ids_with_nodes = set(
                session.scalars(
                    select(HierarchyNode.workspace_id).where(
                        HierarchyNode.assigned_user_id == user_id,
                        HierarchyNode.workspace_id.in_(joined_workspace_ids),
                    )
                ).all()
            )
        return [
            public_workspace(workspace, actor_user_id=user_id)
            for workspace in workspaces
            if workspace.owner_user_id == user_id
            or workspace.workspace_id in workspace_ids_with_nodes
        ]


def create_workspace(
    owner_id: str,
    name: str,
    owner_email: str | None = None,
    owner_name: str | None = None,
) -> dict:
    normalized_name = normalize_workspace_name(name)
    name_key = workspace_name_key(normalized_name)
    owner_email_value = _email_for_user(owner_id, owner_email)
    owner_email_key = normalize_email_key(owner_email_value)

    with session_scope() as session:
        _ensure_user(session, owner_id, owner_email_value, owner_name or owner_email_value)
        duplicate = session.scalar(
            select(Workspace).where(
                Workspace.owner_user_id == owner_id,
                Workspace.name_key == name_key,
            )
        )
        if duplicate is not None:
            raise ValidationError("Workspace name already exists.")

        workspace = Workspace(
            workspace_id=workspace_id_from_name(normalized_name),
            owner_user_id=owner_id,
            name=normalized_name,
            name_key=name_key,
        )
        session.add(workspace)
        session.flush()
        session.add(
            WorkspaceMember(
                workspace_id=workspace.workspace_id,
                user_id=owner_id,
                member_email=owner_email_value,
                member_email_key=owner_email_key,
                added_by_user_id=owner_id,
            )
        )
        public = public_workspace(workspace, actor_user_id=owner_id)

    resolve_storage_context(public["workspace_id"])
    return public


def get_workspace(
    user_id: str,
    workspace_id: str,
    user_email: str | None = None,
) -> dict:
    normalized_id = workspace_id.strip()
    if not normalized_id:
        raise ResourceNotFoundError("Workspace not found.")
    email_key = _email_key_for_user(user_id, user_email)

    with session_scope() as session:
        workspace = session.scalar(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.workspace_id)
            .where(
                Workspace.workspace_id == normalized_id,
                or_(
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.member_email_key == email_key,
                ),
            )
        )
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        if workspace.owner_user_id != user_id and not _user_has_assigned_node(
            session, workspace.workspace_id, user_id
        ):
            raise ResourceNotFoundError("Workspace not found.")
        return public_workspace(workspace, actor_user_id=user_id)


def get_owned_workspace(owner_id: str, workspace_id: str) -> dict:
    return _get_owned_workspace(owner_id, workspace_id)


def resolve_workspace(
    user_id: str,
    name_or_id: str,
    user_email: str | None = None,
) -> dict:
    normalized_value = name_or_id.strip()
    if not normalized_value:
        raise ValidationError("Workspace name is required.")

    email_key = _email_key_for_user(user_id, user_email)
    name_key = workspace_name_key(normalized_value)
    with session_scope() as session:
        workspace = session.scalar(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.workspace_id)
            .where(
                or_(
                    Workspace.workspace_id == normalized_value,
                    Workspace.name_key == name_key,
                ),
                or_(
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.member_email_key == email_key,
                ),
            )
        )
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        if workspace.owner_user_id != user_id and not _user_has_assigned_node(
            session, workspace.workspace_id, user_id
        ):
            raise ResourceNotFoundError("Workspace not found.")
        return public_workspace(workspace, actor_user_id=user_id)


def delete_workspace(owner_id: str, workspace_id: str) -> dict:
    target = _get_owned_workspace(owner_id, workspace_id)
    storage = resolve_storage_context(target["workspace_id"])

    cleanup_errors: list[str] = []
    for repo in list_indexes(workspace_id=target["workspace_id"]):
        repo_id = repo.get("repo_id")
        if repo_id:
            delete_index(repo_id, workspace_id=target["workspace_id"])

    with session_scope() as session:
        workspace = session.get(Workspace, target["workspace_id"])
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        session.delete(workspace)
    for root in storage.cleanup_roots():
        if root.exists():
            try:
                shutil.rmtree(root)
            except OSError as exc:
                cleanup_errors.append(str(exc))

    if owner_id == CLI_OWNER_ID and read_active_workspace_id() == target["workspace_id"]:
        set_active_workspace_id(None)

    if cleanup_errors:
        raise ValidationError(
            "Workspace deleted, but some files could not be removed: "
            + "; ".join(cleanup_errors)
        )
    return target


def list_workspace_members(owner_id: str, workspace_id: str) -> list[dict]:
    _get_owned_workspace(owner_id, workspace_id)
    with session_scope() as session:
        members = session.scalars(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.added_at.asc())
        ).all()
        return [_public_member(member, owner_id=owner_id) for member in members]


def add_workspace_member(owner_id: str, workspace_id: str, email: str) -> dict:
    _get_owned_workspace(owner_id, workspace_id)
    email_key = normalize_email_key(email)
    normalized_email = email.strip()
    with session_scope() as session:
        user = session.scalar(select(User).where(User.email_key == email_key))
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.user_id if user else None,
            member_email=normalized_email,
            member_email_key=email_key,
            added_by_user_id=owner_id,
        )
        session.add(member)
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("Workspace member already exists.") from exc
        return _public_member(member, owner_id=owner_id)


def remove_workspace_member(owner_id: str, workspace_id: str, email: str) -> dict:
    _get_owned_workspace(owner_id, workspace_id)
    email_key = normalize_email_key(email)
    with session_scope() as session:
        member = session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.member_email_key == email_key,
            )
        )
        if member is None:
            raise ResourceNotFoundError("Workspace member not found.")
        if member.user_id == owner_id:
            raise ValidationError("Workspace owner cannot be removed.")
        public = _public_member(member, owner_id=owner_id)
        session.delete(member)
        return public


def leave_workspace(user_id: str, workspace_id: str, user_email: str | None = None) -> dict:
    from src.backend.application.services.hierarchy_graph_service import (
        _revoke_member_access_without_node,
    )

    normalized_id = workspace_id.strip()
    if not normalized_id:
        raise ResourceNotFoundError("Workspace not found.")
    email_key = _email_key_for_user(user_id, user_email)

    with session_scope() as session:
        workspace = session.get(Workspace, normalized_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        if workspace.owner_user_id == user_id:
            raise ValidationError(
                "Workspace owners cannot leave their own workspace. Delete it instead."
            )

        member = session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == normalized_id,
                or_(
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.member_email_key == email_key,
                ),
            )
        )
        if member is None:
            raise ResourceNotFoundError("Workspace not found.")

        public = public_workspace(workspace, actor_user_id=user_id)
        node = session.scalar(
            select(HierarchyNode).where(
                HierarchyNode.workspace_id == normalized_id,
                HierarchyNode.assigned_user_id == user_id,
            )
        )
        if node is not None:
            has_children = session.scalar(
                select(HierarchyConnection.connection_id).where(
                    HierarchyConnection.workspace_id == normalized_id,
                    HierarchyConnection.parent_node_id == node.node_id,
                )
            )
            if has_children is not None:
                raise ValidationError(
                    "You still have people beneath you on the org graph. "
                    "Ask the workspace owner to reassign them before you leave."
                )
            for connection in session.scalars(
                select(HierarchyConnection).where(
                    HierarchyConnection.workspace_id == normalized_id,
                    or_(
                        HierarchyConnection.parent_node_id == node.node_id,
                        HierarchyConnection.child_node_id == node.node_id,
                    ),
                )
            ).all():
                session.delete(connection)
            session.delete(node)
            _revoke_member_access_without_node(session, normalized_id, user_id)
            return public

        for invite in session.scalars(
            select(WorkspaceInvite).where(
                WorkspaceInvite.workspace_id == normalized_id,
                WorkspaceInvite.invitee_user_id == user_id,
                WorkspaceInvite.status == "pending",
            )
        ).all():
            session.delete(invite)
        session.delete(member)
        return public


def user_can_access_workspace(user_id: str, user_email: str, workspace_id: str) -> bool:
    try:
        get_workspace(user_id, workspace_id.strip(), user_email=user_email)
        return True
    except ResourceNotFoundError:
        return False


def workspace_root(workspace_id: str) -> Path:
    return resolve_storage_context(workspace_id).workspace_root


def workspace_repos_dir(workspace_id: str) -> Path:
    return resolve_storage_context(workspace_id).repos_dir


def workspace_indexes_dir(workspace_id: str) -> Path:
    return resolve_storage_context(workspace_id).indexes_dir


def read_active_workspace_id() -> str | None:
    state = _read_cli_state()
    value = state.get("active_workspace_id")
    return value if isinstance(value, str) and value else None


def set_active_workspace_id(workspace_id: str | None) -> None:
    state = _read_cli_state()
    if workspace_id:
        state["active_workspace_id"] = workspace_id
    else:
        state.pop("active_workspace_id", None)
    _write_cli_state(state)


def get_active_workspace() -> dict:
    workspace_id = read_active_workspace_id()
    if not workspace_id:
        raise ResourceNotFoundError('No active workspace. Run: readbase create "workspace name"')
    try:
        return get_workspace(CLI_OWNER_ID, workspace_id)
    except ResourceNotFoundError as exc:
        set_active_workspace_id(None)
        raise ResourceNotFoundError(
            'Active workspace no longer exists. Run: readbase create "workspace name"'
        ) from exc


def public_workspace(
    workspace: Workspace,
    actor_user_id: str | None = None,
) -> dict:
    return {
        "workspace_id": str(workspace.workspace_id),
        "owner_user_id": str(workspace.owner_user_id),
        "name": str(workspace.name),
        "created_at": _format_datetime(workspace.created_at),
        "can_manage": bool(actor_user_id and actor_user_id == workspace.owner_user_id),
    }


def normalize_workspace_name(name: str) -> str:
    normalized = re.sub(r"\s+", " ", name.strip())
    if not normalized:
        raise ValidationError("Workspace name is required.")
    if len(normalized) > 80:
        raise ValidationError("Workspace name must be 80 characters or fewer.")
    return normalized


def workspace_name_key(name: str) -> str:
    return normalize_workspace_name(name).casefold()


def workspace_id_from_name(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-").lower() or "workspace"
    return f"{slug[:48]}-{uuid4().hex[:8]}"


def _get_owned_workspace(owner_id: str, workspace_id: str) -> dict:
    normalized_id = workspace_id.strip()
    with session_scope() as session:
        workspace = session.get(Workspace, normalized_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        if workspace.owner_user_id != owner_id:
            raise PermissionDeniedError("Workspace owner access required.")
        return public_workspace(workspace, actor_user_id=owner_id)


def _ensure_user(session, user_id: str, email: str, name: str) -> User:
    email_key = normalize_email_key(email)
    user = session.get(User, user_id)
    if user is None:
        user = session.scalar(select(User).where(User.email_key == email_key))
    if user is None:
        user = User(user_id=user_id, email=email, email_key=email_key, name=name)
        session.add(user)
    else:
        user.email = email
        user.email_key = email_key
        user.name = name
    return user


def _public_member(member: WorkspaceMember, owner_id: str) -> dict:
    is_owner = member.user_id == owner_id
    return {
        "email": member.member_email,
        "user_id": member.user_id,
        "added_at": _format_datetime(member.added_at),
        "is_owner": is_owner,
        "connector_manager": bool(is_owner or member.connector_manager),
    }


def _user_has_assigned_node(session, workspace_id: str, user_id: str) -> bool:
    return (
        session.scalar(
            select(HierarchyNode.node_id).where(
                HierarchyNode.workspace_id == workspace_id,
                HierarchyNode.assigned_user_id == user_id,
            )
        )
        is not None
    )


def _email_for_user(user_id: str, user_email: str | None) -> str:
    if user_email:
        return user_email.strip()
    if "@" in user_id:
        return user_id.strip()
    return f"{user_id}@local.readbase"


def _email_key_for_user(user_id: str, user_email: str | None) -> str:
    return normalize_email_key(_email_for_user(user_id, user_email))


def _format_datetime(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _read_cli_state() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if not CLI_STATE_FILE.exists():
        return {}
    try:
        data = json.loads(CLI_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_cli_state(state: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CLI_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
