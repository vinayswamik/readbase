from __future__ import annotations

from pathlib import Path

from src.backend.config.settings import DATA_DIR
from src.backend.infrastructure.storage.context import StorageContext
from src.backend.infrastructure.storage.deployment import DeploymentMode, org_storage_root


def legacy_workspace_root(workspace_id: str) -> Path:
    return DATA_DIR / "workspaces" / workspace_id


def saas_workspace_root(owner_user_id: str, workspace_id: str) -> Path:
    return DATA_DIR / "owners" / owner_user_id / "workspaces" / workspace_id


def customer_project_root(workspace_id: str, *, storage_root: Path | None = None) -> Path:
    root = storage_root or org_storage_root()
    if root is None:
        raise ValueError("READBASE_ORG_STORAGE_ROOT is required for customer deployment mode.")
    return root / "projects" / workspace_id


def org_workspace_root(org_storage_root_path: Path, workspace_id: str) -> Path:
    return org_storage_root_path / "projects" / workspace_id


def workspace_dirs(workspace_root: Path) -> tuple[Path, Path, Path]:
    return (
        workspace_root / "repos",
        workspace_root / "indexes",
        workspace_root / "chroma",
    )


def build_workspace_context(
    *,
    deployment: DeploymentMode,
    owner_user_id: str,
    workspace_id: str,
    org_storage_root_path: Path | None = None,
) -> StorageContext:
    if org_storage_root_path is not None:
        root = org_workspace_root(org_storage_root_path, workspace_id)
        legacy = legacy_workspace_root(workspace_id)
    elif deployment is DeploymentMode.CUSTOMER:
        root = customer_project_root(workspace_id)
        legacy = None
    else:
        root = saas_workspace_root(owner_user_id, workspace_id)
        legacy = legacy_workspace_root(workspace_id)
    repos_dir, indexes_dir, chroma_dir = workspace_dirs(root)
    return StorageContext(
        deployment_mode=deployment,
        owner_user_id=owner_user_id,
        workspace_id=workspace_id,
        workspace_root=root,
        repos_dir=repos_dir,
        indexes_dir=indexes_dir,
        chroma_dir=chroma_dir,
        legacy_workspace_root=legacy,
    )


def build_cli_context() -> StorageContext:
    root = DATA_DIR
    return StorageContext(
        deployment_mode=DeploymentMode.SAAS,
        owner_user_id=None,
        workspace_id=None,
        workspace_root=root,
        repos_dir=root / "repos",
        indexes_dir=root / "indexes",
        chroma_dir=root / "chroma",
        legacy_workspace_root=None,
    )
