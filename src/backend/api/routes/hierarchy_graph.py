from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.api.auth import require_authenticated_user, require_workspace_access
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import (
    CreateHierarchyConnectionRequest,
    CreateHierarchyNodeRequest,
    CreateHierarchyNodeResponse,
    HierarchyConnectionResponse,
    HierarchyGraphResponse,
    HierarchyNodeResponse,
    UpdateHierarchyNodeRequest,
)
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.hierarchy_graph_service import (
    create_hierarchy_connection,
    create_hierarchy_node,
    delete_hierarchy_connection,
    delete_hierarchy_node,
    get_workspace_graph,
    update_hierarchy_node,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/graph", tags=["hierarchy graph"])


@router.get("", response_model=HierarchyGraphResponse)
def workspace_graph(
    workspace_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return get_workspace_graph(workspace_id, user)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/nodes", response_model=CreateHierarchyNodeResponse)
def create_node_endpoint(
    workspace_id: str,
    payload: CreateHierarchyNodeRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return create_hierarchy_node(
            workspace_id,
            user,
            display_name=payload.display_name,
            assigned_user_id=payload.assigned_user_id,
            invitee_email=payload.invitee_email,
            invite_method=payload.invite_method,
            invitor_designation=payload.invitor_designation,
            relation=payload.relation,
            reason=payload.reason,
            x=payload.x,
            y=payload.y,
            parent_node_id=payload.parent_node_id,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.patch("/nodes/{node_id}", response_model=HierarchyNodeResponse)
def update_node_endpoint(
    workspace_id: str,
    node_id: str,
    payload: UpdateHierarchyNodeRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return update_hierarchy_node(
            workspace_id,
            user,
            node_id,
            display_name=payload.display_name,
            assigned_user_id=payload.assigned_user_id,
            parent_node_id=payload.parent_node_id,
            x=payload.x,
            y=payload.y,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/nodes/{node_id}", response_model=HierarchyNodeResponse)
def delete_node_endpoint(
    workspace_id: str,
    node_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return delete_hierarchy_node(workspace_id, user, node_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/connections", response_model=HierarchyConnectionResponse)
def create_connection_endpoint(
    workspace_id: str,
    payload: CreateHierarchyConnectionRequest,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return create_hierarchy_connection(
            workspace_id,
            user,
            parent_node_id=payload.parent_node_id,
            child_node_id=payload.child_node_id,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.delete("/connections/{connection_id}", response_model=HierarchyConnectionResponse)
def delete_connection_endpoint(
    workspace_id: str,
    connection_id: str,
    user=Depends(require_authenticated_user),
    _workspace=Depends(require_workspace_access),
) -> dict:
    try:
        return delete_hierarchy_connection(workspace_id, user, connection_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
