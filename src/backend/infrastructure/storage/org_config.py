from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from src.backend.application.services.exceptions import ResourceNotFoundError
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.storage_models import OrganizationStorageConfig


def org_storage_root(org_id: str) -> Path:
    normalized = org_id.strip()
    if not normalized:
        raise ResourceNotFoundError("Organization not found.")

    with session_scope() as session:
        config = session.get(OrganizationStorageConfig, normalized)
        if config is None:
            raise ResourceNotFoundError("Organization storage is not configured.")
        raw_root = config.storage_root.strip()
        if not raw_root:
            raise ResourceNotFoundError("Organization storage is not configured.")

    path = Path(raw_root).expanduser()
    if not path.is_absolute():
        from src.backend.config.settings import DATA_DIR

        path = DATA_DIR / path
    return path


def org_blob_backend(org_id: str) -> str:
    with session_scope() as session:
        config = session.get(OrganizationStorageConfig, org_id.strip())
        if config is None:
            return "local"
        return config.blob_backend.strip().lower() or "local"


def load_org_storage_config(org_id: str) -> OrganizationStorageConfig | None:
    with session_scope() as session:
        return session.get(OrganizationStorageConfig, org_id.strip())
