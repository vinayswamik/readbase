from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import (
    AssignWorkspaceOrganizationRequest,
    CreateOrganizationRequest,
    OrganizationResponse,
    UpdateOrganizationStorageRequest,
    WorkspaceOrganizationResponse,
)
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.organization_service import (
    assign_workspace_to_organization,
    create_organization,
    get_organization,
    update_organization_storage,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse)
def create_organization_endpoint(
    payload: CreateOrganizationRequest,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return create_organization(
            user.user_id,
            payload.name,
            payload.storage_root,
            blob_backend=payload.blob_backend,
            owner_email=user.email,
            owner_name=user.name,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization_endpoint(org_id: str, user=Depends(require_authenticated_user)) -> dict:
    try:
        return get_organization(user.user_id, org_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.patch("/{org_id}/storage", response_model=OrganizationResponse)
def update_organization_storage_endpoint(
    org_id: str,
    payload: UpdateOrganizationStorageRequest,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return update_organization_storage(
            user.user_id,
            org_id,
            storage_root=payload.storage_root,
            blob_backend=payload.blob_backend,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc


@router.post("/{org_id}/workspaces", response_model=WorkspaceOrganizationResponse)
def assign_workspace_organization_endpoint(
    org_id: str,
    payload: AssignWorkspaceOrganizationRequest,
    user=Depends(require_authenticated_user),
) -> dict:
    try:
        return assign_workspace_to_organization(
            user.user_id,
            payload.workspace_id,
            org_id,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
