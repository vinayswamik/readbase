from __future__ import annotations

from src.backend.application.services.exceptions import ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import Workspace
from src.backend.infrastructure.storage.context import StorageContext
from src.backend.infrastructure.storage.deployment import deployment_mode
from src.backend.infrastructure.storage.org_config import org_storage_root
from src.backend.infrastructure.storage.paths import build_cli_context, build_workspace_context


def resolve_storage(workspace_id: str | None) -> StorageContext:
    if workspace_id:
        return resolve_storage_context(workspace_id)
    return resolve_cli_storage_context()


def resolve_storage_context(workspace_id: str) -> StorageContext:
    normalized = workspace_id.strip()
    if not normalized:
        raise ResourceNotFoundError("Workspace not found.")

    with session_scope() as session:
        workspace = session.get(Workspace, normalized)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found.")
        owner_user_id = workspace.owner_user_id
        organization_id = workspace.organization_id

    org_root = None
    if organization_id:
        org_root = org_storage_root(organization_id)

    context = build_workspace_context(
        deployment=deployment_mode(),
        owner_user_id=owner_user_id,
        workspace_id=normalized,
        org_storage_root_path=org_root,
    )
    context.ensure_dirs()
    return context


def resolve_cli_storage_context() -> StorageContext:
    context = build_cli_context()
    context.ensure_dirs()
    return context
