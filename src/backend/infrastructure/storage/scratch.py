from __future__ import annotations

from pathlib import Path

from src.backend.infrastructure.storage.context import StorageContext
from src.backend.infrastructure.storage.deployment import scratch_dir


def workspace_scratch_dir(context: StorageContext) -> Path:
    base = scratch_dir()
    base.mkdir(parents=True, exist_ok=True)
    if context.workspace_id:
        path = base / context.workspace_id
    else:
        path = base / "cli"
    path.mkdir(parents=True, exist_ok=True)
    return path
