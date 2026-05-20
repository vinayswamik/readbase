from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.auth_service import AuthUser
from src.backend.application.services.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import (
    HierarchyConnection,
    HierarchyNode,
    User,
    Workspace,
    WorkspaceMember,
)


def get_workspace_graph(workspace_id: str, user: AuthUser) -> dict:
    with session_scope() as session:
        nodes = session.scalars(
            select(HierarchyNode)
            .where(HierarchyNode.workspace_id == workspace_id)
            .order_by(HierarchyNode.created_at.asc())
        ).all()
        connections = session.scalars(
            select(HierarchyConnection)
            .where(HierarchyConnection.workspace_id == workspace_id)
            .order_by(HierarchyConnection.created_at.asc())
        ).all()
        users_by_id = _workspace_users_by_id(session, workspace_id)
        visible_nodes, visible_connections = _visible_graph_for_user(nodes, connections, user)
        return {
            "nodes": [_public_node(node, users_by_id) for node in visible_nodes],
            "connections": [_public_connection(connection) for connection in visible_connections],
            "assignable_users": list(users_by_id.values()),
        }


def create_hierarchy_node(
    workspace_id: str,
    user: AuthUser,
    *,
    display_name: str,
    assigned_user_id: str,
    x: float = 0,
    y: float = 0,
    parent_node_id: str | None = None,
) -> dict:
    normalized_display_name = _normalize_display_name(display_name)

    with session_scope() as session:
        users_by_id = _workspace_users_by_id(session, workspace_id)
        if assigned_user_id not in users_by_id:
            raise ValidationError("Assigned user must be a logged-in workspace member.")
        if _node_for_assigned_user(session, workspace_id, assigned_user_id) is not None:
            raise ValidationError("Assigned user already has a hierarchy node.")

        parent = None
        if user.role == "admin":
            if parent_node_id:
                parent = _get_node(session, workspace_id, parent_node_id)
        else:
            parent = _member_parent_node(session, workspace_id, user, parent_node_id)

        node = HierarchyNode(
            node_id=_new_id("node"),
            workspace_id=workspace_id,
            display_name=normalized_display_name,
            assigned_user_id=assigned_user_id,
            x=float(x),
            y=float(y),
            created_by_user_id=user.user_id,
        )
        session.add(node)
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("Assigned user already has a hierarchy node.") from exc

        connection = None
        if parent is not None:
            connection = _create_connection(session, workspace_id, user, parent, node)
        return {
            "node": _public_node(node, users_by_id),
            "connection": _public_connection(connection) if connection else None,
        }


def update_hierarchy_node(
    workspace_id: str,
    user: AuthUser,
    node_id: str,
    *,
    display_name: str | None = None,
    assigned_user_id: str | None = None,
    parent_node_id: str | None = None,
    x: float | None = None,
    y: float | None = None,
) -> dict:
    if all(value is None for value in (display_name, assigned_user_id, parent_node_id, x, y)):
        raise ValidationError("No node changes provided.")

    with session_scope() as session:
        node = _get_node(session, workspace_id, node_id)
        users_by_id = _workspace_users_by_id(session, workspace_id)
        changing_management_fields = (
            display_name is not None or assigned_user_id is not None or parent_node_id is not None
        )
        if changing_management_fields and user.role != "admin":
            raise PermissionDeniedError("Only admins can rename, reassign, or reparent nodes.")

        if display_name is not None:
            node.display_name = _normalize_display_name(display_name)
        if assigned_user_id is not None and assigned_user_id != node.assigned_user_id:
            if assigned_user_id not in users_by_id:
                raise ValidationError("Assigned user must be a logged-in workspace member.")
            if _node_for_assigned_user(session, workspace_id, assigned_user_id) is not None:
                raise ValidationError("Assigned user already has a hierarchy node.")
            node.assigned_user_id = assigned_user_id
        if x is not None:
            node.x = float(x)
        if y is not None:
            node.y = float(y)
        if parent_node_id is not None:
            _reparent_node(session, workspace_id, user, node, parent_node_id)

        node.updated_at = utc_now()
        session.flush()
        return _public_node(node, users_by_id)


def delete_hierarchy_node(workspace_id: str, user: AuthUser, node_id: str) -> dict:
    with session_scope() as session:
        node = _get_node(session, workspace_id, node_id)
        users_by_id = _workspace_users_by_id(session, workspace_id)
        _ensure_can_delete_node(session, workspace_id, user, node)
        public = _public_node(node, users_by_id)
        for connection in session.scalars(
            select(HierarchyConnection).where(
                HierarchyConnection.workspace_id == workspace_id,
                or_(
                    HierarchyConnection.parent_node_id == node.node_id,
                    HierarchyConnection.child_node_id == node.node_id,
                ),
            )
        ).all():
            session.delete(connection)
        session.delete(node)
        return public


def create_hierarchy_connection(
    workspace_id: str,
    user: AuthUser,
    *,
    parent_node_id: str,
    child_node_id: str,
) -> dict:
    if user.role != "admin":
        raise PermissionDeniedError("Only admins can manually connect nodes.")
    with session_scope() as session:
        parent = _get_node(session, workspace_id, parent_node_id)
        child = _get_node(session, workspace_id, child_node_id)
        connection = _create_connection(session, workspace_id, user, parent, child)
        return _public_connection(connection)


def delete_hierarchy_connection(workspace_id: str, user: AuthUser, connection_id: str) -> dict:
    if user.role != "admin":
        raise PermissionDeniedError("Only admins can remove connections.")
    with session_scope() as session:
        connection = _get_connection(session, workspace_id, connection_id)
        public = _public_connection(connection)
        session.delete(connection)
        return public


def _create_connection(
    session,
    workspace_id: str,
    user: AuthUser,
    parent: HierarchyNode,
    child: HierarchyNode,
) -> HierarchyConnection:
    if parent.node_id == child.node_id:
        raise ValidationError("A node cannot connect to itself.")
    if user.role != "admin" and parent.assigned_user_id != user.user_id:
        raise PermissionDeniedError("Members can create children only under their own node.")
    if _would_create_cycle(session, workspace_id, parent.node_id, child.node_id):
        raise ValidationError("Connection would create a cycle.")

    connection = HierarchyConnection(
        connection_id=_new_id("edge"),
        workspace_id=workspace_id,
        parent_node_id=parent.node_id,
        child_node_id=child.node_id,
        created_by_user_id=user.user_id,
    )
    session.add(connection)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ValidationError("Child node already has a parent connection.") from exc
    return connection


def _reparent_node(
    session,
    workspace_id: str,
    user: AuthUser,
    node: HierarchyNode,
    parent_node_id: str,
) -> None:
    if user.role != "admin":
        raise PermissionDeniedError("Only admins can reparent nodes.")
    if parent_node_id == "":
        for connection in _incoming_connections(session, workspace_id, node.node_id):
            session.delete(connection)
        return

    parent = _get_node(session, workspace_id, parent_node_id)
    if parent.node_id == node.node_id:
        raise ValidationError("A node cannot connect to itself.")
    for connection in _incoming_connections(session, workspace_id, node.node_id):
        session.delete(connection)
    session.flush()
    _create_connection(session, workspace_id, user, parent, node)


def _member_parent_node(
    session,
    workspace_id: str,
    user: AuthUser,
    parent_node_id: str | None,
) -> HierarchyNode:
    own_node = _node_for_assigned_user(session, workspace_id, user.user_id)
    if own_node is None:
        raise PermissionDeniedError("Members need their own assigned node before creating children.")
    if parent_node_id != own_node.node_id:
        raise PermissionDeniedError("Members can create children only under their own node.")
    return own_node


def _ensure_can_delete_node(
    session,
    workspace_id: str,
    user: AuthUser,
    node: HierarchyNode,
) -> None:
    if user.role == "admin":
        return
    if node.assigned_user_id == user.user_id:
        raise PermissionDeniedError("Members cannot delete their own node.")
    own_node = _node_for_assigned_user(session, workspace_id, user.user_id)
    if own_node is None:
        raise PermissionDeniedError("Members need their own assigned node before deleting children.")
    direct_child = session.scalar(
        select(HierarchyConnection).where(
            HierarchyConnection.workspace_id == workspace_id,
            HierarchyConnection.parent_node_id == own_node.node_id,
            HierarchyConnection.child_node_id == node.node_id,
        )
    )
    if direct_child is None:
        raise PermissionDeniedError("Members can delete only immediate child nodes.")
    has_children = session.scalar(
        select(HierarchyConnection).where(
            HierarchyConnection.workspace_id == workspace_id,
            HierarchyConnection.parent_node_id == node.node_id,
        )
    )
    if has_children is not None:
        raise PermissionDeniedError("Members can delete only leaf child nodes.")


def _would_create_cycle(
    session,
    workspace_id: str,
    parent_node_id: str,
    child_node_id: str,
) -> bool:
    descendants = {child_node_id}
    frontier = [child_node_id]
    while frontier:
        current = frontier.pop()
        child_connections = session.scalars(
            select(HierarchyConnection).where(
                HierarchyConnection.workspace_id == workspace_id,
                HierarchyConnection.parent_node_id == current,
            )
        ).all()
        for connection in child_connections:
            next_child = connection.child_node_id
            if next_child == parent_node_id:
                return True
            if next_child not in descendants:
                descendants.add(next_child)
                frontier.append(next_child)
    return False


def _visible_graph_for_user(
    nodes: list[HierarchyNode],
    connections: list[HierarchyConnection],
    user: AuthUser,
) -> tuple[list[HierarchyNode], list[HierarchyConnection]]:
    if user.role == "admin":
        return nodes, connections

    own_node = next((node for node in nodes if node.assigned_user_id == user.user_id), None)
    if own_node is None:
        return [], []

    children_by_parent: dict[str, list[str]] = {}
    parent_by_child: dict[str, str] = {}
    for connection in connections:
        children_by_parent.setdefault(connection.parent_node_id, []).append(connection.child_node_id)
        parent_by_child[connection.child_node_id] = connection.parent_node_id

    visible_node_ids = {own_node.node_id}
    parent_id = parent_by_child.get(own_node.node_id)
    if parent_id:
        visible_node_ids.add(parent_id)

    frontier = deque([(own_node.node_id, 0)])
    while frontier:
        parent_id, depth = frontier.popleft()
        if depth >= 2:
            continue
        for child_id in children_by_parent.get(parent_id, []):
            if child_id in visible_node_ids:
                continue
            visible_node_ids.add(child_id)
            frontier.append((child_id, depth + 1))

    visible_nodes = [node for node in nodes if node.node_id in visible_node_ids]
    visible_connections = [
        connection
        for connection in connections
        if connection.parent_node_id in visible_node_ids
        and connection.child_node_id in visible_node_ids
    ]
    return visible_nodes, visible_connections


def _get_node(session, workspace_id: str, node_id: str) -> HierarchyNode:
    node = session.scalar(
        select(HierarchyNode).where(
            HierarchyNode.workspace_id == workspace_id,
            HierarchyNode.node_id == node_id,
        )
    )
    if node is None:
        raise ResourceNotFoundError("Hierarchy node not found.")
    return node


def _get_connection(session, workspace_id: str, connection_id: str) -> HierarchyConnection:
    connection = session.scalar(
        select(HierarchyConnection).where(
            HierarchyConnection.workspace_id == workspace_id,
            HierarchyConnection.connection_id == connection_id,
        )
    )
    if connection is None:
        raise ResourceNotFoundError("Hierarchy connection not found.")
    return connection


def _incoming_connections(session, workspace_id: str, node_id: str) -> list[HierarchyConnection]:
    return list(
        session.scalars(
            select(HierarchyConnection).where(
                HierarchyConnection.workspace_id == workspace_id,
                HierarchyConnection.child_node_id == node_id,
            )
        ).all()
    )


def _node_for_assigned_user(
    session,
    workspace_id: str,
    assigned_user_id: str,
) -> HierarchyNode | None:
    return session.scalar(
        select(HierarchyNode).where(
            HierarchyNode.workspace_id == workspace_id,
            HierarchyNode.assigned_user_id == assigned_user_id,
        )
    )


def _workspace_users_by_id(session, workspace_id: str) -> dict[str, dict]:
    workspace = session.get(Workspace, workspace_id)
    owner_user_id = workspace.owner_user_id if workspace else None
    rows = session.execute(
        select(WorkspaceMember, User)
        .join(User, User.user_id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id.is_not(None),
        )
        .order_by(WorkspaceMember.added_at.asc())
    ).all()
    return {
        user.user_id: {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "is_owner": user.user_id == owner_user_id,
        }
        for _, user in rows
    }


def _normalize_display_name(display_name: str) -> str:
    normalized = " ".join(display_name.strip().split())
    if not normalized:
        raise ValidationError("Display name is required.")
    if len(normalized) > 120:
        raise ValidationError("Display name must be 120 characters or fewer.")
    return normalized


def _public_node(node: HierarchyNode, users_by_id: dict[str, dict]) -> dict:
    assigned_user = users_by_id.get(node.assigned_user_id, {})
    return {
        "node_id": node.node_id,
        "workspace_id": node.workspace_id,
        "display_name": node.display_name,
        "assigned_user_id": node.assigned_user_id,
        "assigned_user_email": assigned_user.get("email"),
        "assigned_user_name": assigned_user.get("name"),
        "x": node.x,
        "y": node.y,
        "created_by_user_id": node.created_by_user_id,
        "created_at": _format_datetime(node.created_at),
        "updated_at": _format_datetime(node.updated_at),
    }


def _public_connection(connection: HierarchyConnection) -> dict:
    return {
        "connection_id": connection.connection_id,
        "workspace_id": connection.workspace_id,
        "parent_node_id": connection.parent_node_id,
        "child_node_id": connection.child_node_id,
        "created_by_user_id": connection.created_by_user_id,
        "created_at": _format_datetime(connection.created_at),
    }


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:16]}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_datetime(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
