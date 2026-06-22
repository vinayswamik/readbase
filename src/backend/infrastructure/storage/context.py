from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.backend.infrastructure.storage.deployment import DeploymentMode


@dataclass(frozen=True, slots=True)
class StorageContext:
    deployment_mode: DeploymentMode
    owner_user_id: str | None
    workspace_id: str | None
    workspace_root: Path
    repos_dir: Path
    indexes_dir: Path
    chroma_dir: Path
    legacy_workspace_root: Path | None = None

    def ensure_dirs(self) -> None:
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.indexes_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

    def index_search_dirs(self) -> tuple[Path, ...]:
        dirs: list[Path] = [self.indexes_dir]
        if self.legacy_workspace_root is not None:
            legacy_indexes = self.legacy_workspace_root / "indexes"
            if legacy_indexes not in dirs:
                dirs.append(legacy_indexes)
        return tuple(dirs)

    def cleanup_roots(self) -> tuple[Path, ...]:
        roots: list[Path] = [self.workspace_root]
        if self.legacy_workspace_root is not None and self.legacy_workspace_root not in roots:
            roots.append(self.legacy_workspace_root)
        return tuple(roots)
