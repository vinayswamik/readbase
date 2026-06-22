from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from src.backend.config.settings import DATA_DIR
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import Workspace
from src.backend.infrastructure.storage.paths import legacy_workspace_root, saas_workspace_root


@dataclass(frozen=True)
class MigrationResult:
    workspace_id: str
    owner_user_id: str
    source: Path
    destination: Path
    moved: bool
    skipped_reason: str | None = None


def plan_legacy_migrations() -> list[MigrationResult]:
    results: list[MigrationResult] = []
    with session_scope() as session:
        workspace_rows = [
            (workspace.workspace_id, workspace.owner_user_id)
            for workspace in session.scalars(select(Workspace)).all()
        ]

    for workspace_id, owner_user_id in workspace_rows:
        source = legacy_workspace_root(workspace_id)
        destination = saas_workspace_root(owner_user_id, workspace_id)
        if not source.exists():
            results.append(
                MigrationResult(
                    workspace_id=workspace_id,
                    owner_user_id=owner_user_id,
                    source=source,
                    destination=destination,
                    moved=False,
                    skipped_reason="legacy path does not exist",
                )
            )
            continue
        if destination.exists():
            results.append(
                MigrationResult(
                    workspace_id=workspace_id,
                    owner_user_id=owner_user_id,
                    source=source,
                    destination=destination,
                    moved=False,
                    skipped_reason="destination already exists",
                )
            )
            continue
        results.append(
            MigrationResult(
                workspace_id=workspace_id,
                owner_user_id=owner_user_id,
                source=source,
                destination=destination,
                moved=True,
            )
        )
    return results


def migrate_legacy_layout(*, dry_run: bool = True) -> list[MigrationResult]:
    executed: list[MigrationResult] = []
    for item in plan_legacy_migrations():
        if not item.moved:
            executed.append(item)
            continue
        if dry_run:
            executed.append(item)
            continue
        item.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(item.source), str(item.destination))
        executed.append(item)
    return executed


def legacy_workspaces_dir() -> Path:
    return DATA_DIR / "workspaces"
