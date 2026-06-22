from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.backend.application.services.auth_service import normalize_email_key as normalize_user_email_key
from src.backend.application.services.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import User, Workspace
from src.backend.infrastructure.storage.org_config import load_org_storage_config
from src.backend.infrastructure.storage_models import (
    Organization,
    OrganizationMember,
    OrganizationStorageConfig,
)


def normalize_org_name(name: str) -> str:
    normalized = re.sub(r"\s+", " ", name.strip())
    if not normalized:
        raise ValidationError("Organization name is required.")
    if len(normalized) > 120:
        raise ValidationError("Organization name is too long.")
    return normalized


def org_name_key(name: str) -> str:
    return normalize_org_name(name).casefold()


def create_organization(
    owner_user_id: str,
    name: str,
    storage_root: str,
    *,
    blob_backend: str = "local",
    owner_email: str | None = None,
    owner_name: str | None = None,
) -> dict:
    normalized_name = normalize_org_name(name)
    normalized_root = storage_root.strip()
    if not normalized_root:
        raise ValidationError("storage_root is required.")

    backend = blob_backend.strip().lower() or "local"
    if backend not in {"local", "s3"}:
        raise ValidationError("blob_backend must be local or s3.")

    with session_scope() as session:
        _ensure_user(session, owner_user_id, owner_email, owner_name)
        org = Organization(
            org_id=f"org-{uuid4().hex[:12]}",
            name=normalized_name,
            name_key=org_name_key(normalized_name),
        )
        session.add(org)
        session.add(
            OrganizationMember(
                org_id=org.org_id,
                user_id=owner_user_id,
                role="admin",
            )
        )
        session.add(
            OrganizationStorageConfig(
                org_id=org.org_id,
                blob_backend=backend,
                storage_root=normalized_root,
            )
        )
        try:
            session.flush()
        except IntegrityError as exc:
            raise ValidationError("Organization name already exists.") from exc
        return public_organization(org, role="admin")


def get_organization(user_id: str, org_id: str) -> dict:
    membership = _require_org_member(user_id, org_id)
    with session_scope() as session:
        org = session.get(Organization, org_id.strip())
        if org is None:
            raise ResourceNotFoundError("Organization not found.")
        return public_organization(org, role=membership["role"])


def update_organization_storage(
    user_id: str,
    org_id: str,
    *,
    storage_root: str,
    blob_backend: str | None = None,
) -> dict:
    _require_org_admin(user_id, org_id)
    normalized_root = storage_root.strip()
    if not normalized_root:
        raise ValidationError("storage_root is required.")

    with session_scope() as session:
        config = session.get(OrganizationStorageConfig, org_id.strip())
        if config is None:
            raise ResourceNotFoundError("Organization storage is not configured.")
        config.storage_root = normalized_root
        if blob_backend is not None:
            backend = blob_backend.strip().lower() or "local"
            if backend not in {"local", "s3"}:
                raise ValidationError("blob_backend must be local or s3.")
            config.blob_backend = backend
        org = session.get(Organization, org_id.strip())
        if org is None:
            raise ResourceNotFoundError("Organization not found.")
        return public_organization(org, role="admin", config=config)


def assign_workspace_to_organization(
    owner_user_id: str,
    workspace_id: str,
    org_id: str,
) -> dict:
    _require_org_admin(owner_user_id, org_id)
    with session_scope() as session:
        workspace = session.get(Workspace, workspace_id.strip())
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        if workspace.owner_user_id != owner_user_id:
            raise PermissionDeniedError("Workspace owner access required.")
        org = session.get(Organization, org_id.strip())
        if org is None:
            raise ResourceNotFoundError("Organization not found.")
        workspace.organization_id = org.org_id
        return {
            "workspace_id": workspace.workspace_id,
            "organization_id": org.org_id,
        }


def _require_org_member(user_id: str, org_id: str) -> dict:
    with session_scope() as session:
        membership = session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.org_id == org_id.strip(),
                OrganizationMember.user_id == user_id,
            )
        )
        if membership is None:
            raise PermissionDeniedError("Organization access required.")
        return {"role": membership.role}


def _require_org_admin(user_id: str, org_id: str) -> dict:
    membership = _require_org_member(user_id, org_id)
    if membership["role"] != "admin":
        raise PermissionDeniedError("Organization admin access required.")
    return membership


def _ensure_user(session, user_id: str, email: str | None, name: str | None) -> None:
    user = session.get(User, user_id)
    if user is not None:
        return
    if not email:
        raise ValidationError("User email is required.")
    session.add(
        User(
            user_id=user_id,
            email=email,
            email_key=normalize_user_email_key(email),
            name=name or email,
        )
    )


def public_organization(
    org: Organization,
    *,
    role: str,
    config: OrganizationStorageConfig | None = None,
) -> dict:
    storage = config or load_org_storage_config(org.org_id)
    return {
        "org_id": org.org_id,
        "name": org.name,
        "role": role,
        "storage": {
            "blob_backend": storage.blob_backend if storage else "local",
            "storage_root": storage.storage_root if storage else "",
        },
    }
