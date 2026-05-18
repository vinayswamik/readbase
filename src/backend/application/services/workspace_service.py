from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.backend.application.services.exceptions import ResourceNotFoundError, ValidationError
from src.backend.config.settings import CLI_STATE_FILE, DATA_DIR, WORKSPACES_DIR, WORKSPACES_MANIFEST
from src.backend.infrastructure.ingestion.repo_manager import list_indexes
from src.backend.infrastructure.retrieval.retriever import delete_index

CLI_OWNER_ID = "local-cli"


def list_workspaces(owner_id: str) -> list[dict]:
    return [
        public_workspace(workspace)
        for workspace in _read_manifest()
        if workspace.get("owner_id") == owner_id
    ]


def create_workspace(owner_id: str, name: str) -> dict:
    normalized_name = normalize_workspace_name(name)
    name_key = workspace_name_key(normalized_name)
    workspaces = _read_manifest()
    if any(
        workspace.get("owner_id") == owner_id and workspace.get("name_key") == name_key
        for workspace in workspaces
    ):
        raise ValidationError("Workspace name already exists.")

    workspace = {
        "workspace_id": workspace_id_from_name(normalized_name),
        "owner_id": owner_id,
        "name": normalized_name,
        "name_key": name_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    workspaces.append(workspace)
    _write_manifest(workspaces)
    workspace_root(workspace["workspace_id"]).mkdir(parents=True, exist_ok=True)
    return public_workspace(workspace)


def get_workspace(owner_id: str, workspace_id: str) -> dict:
    normalized_id = workspace_id.strip()
    for workspace in _read_manifest():
        if workspace.get("owner_id") == owner_id and workspace.get("workspace_id") == normalized_id:
            return public_workspace(workspace)
    raise ResourceNotFoundError("Workspace not found.")


def resolve_workspace(owner_id: str, name_or_id: str) -> dict:
    normalized_value = name_or_id.strip()
    if not normalized_value:
        raise ValidationError("Workspace name is required.")

    name_key = workspace_name_key(normalized_value)
    for workspace in _read_manifest():
        if workspace.get("owner_id") != owner_id:
            continue
        if workspace.get("workspace_id") == normalized_value or workspace.get("name_key") == name_key:
            return public_workspace(workspace)
    raise ResourceNotFoundError("Workspace not found.")


def delete_workspace(owner_id: str, workspace_id: str) -> dict:
    target = get_workspace(owner_id, workspace_id)
    workspaces = _read_manifest()
    remaining = [
        workspace
        for workspace in workspaces
        if not (
            workspace.get("owner_id") == owner_id
            and workspace.get("workspace_id") == target["workspace_id"]
        )
    ]
    _write_manifest(remaining)

    cleanup_errors: list[str] = []
    for repo in list_indexes(workspace_id=target["workspace_id"]):
        repo_id = repo.get("repo_id")
        if repo_id:
            delete_index(repo_id, workspace_id=target["workspace_id"])

    root = workspace_root(target["workspace_id"])
    if root.exists():
        try:
            shutil.rmtree(root)
        except OSError as exc:
            cleanup_errors.append(str(exc))

    if owner_id == CLI_OWNER_ID and read_active_workspace_id() == target["workspace_id"]:
        set_active_workspace_id(None)

    if cleanup_errors:
        raise ValidationError(
            "Workspace deleted, but some files could not be removed: "
            + "; ".join(cleanup_errors)
        )
    return target


def workspace_root(workspace_id: str) -> Path:
    return WORKSPACES_DIR / workspace_id


def workspace_repos_dir(workspace_id: str) -> Path:
    return workspace_root(workspace_id) / "repos"


def workspace_indexes_dir(workspace_id: str) -> Path:
    return workspace_root(workspace_id) / "indexes"


def read_active_workspace_id() -> str | None:
    state = _read_cli_state()
    value = state.get("active_workspace_id")
    return value if isinstance(value, str) and value else None


def set_active_workspace_id(workspace_id: str | None) -> None:
    state = _read_cli_state()
    if workspace_id:
        state["active_workspace_id"] = workspace_id
    else:
        state.pop("active_workspace_id", None)
    _write_cli_state(state)


def get_active_workspace() -> dict:
    workspace_id = read_active_workspace_id()
    if not workspace_id:
        raise ResourceNotFoundError('No active workspace. Run: readbase create "workspace name"')
    try:
        return get_workspace(CLI_OWNER_ID, workspace_id)
    except ResourceNotFoundError as exc:
        set_active_workspace_id(None)
        raise ResourceNotFoundError(
            'Active workspace no longer exists. Run: readbase create "workspace name"'
        ) from exc


def public_workspace(workspace: dict) -> dict:
    return {
        "workspace_id": str(workspace.get("workspace_id", "")),
        "name": str(workspace.get("name", "")),
        "created_at": str(workspace.get("created_at", "")),
    }


def normalize_workspace_name(name: str) -> str:
    normalized = re.sub(r"\s+", " ", name.strip())
    if not normalized:
        raise ValidationError("Workspace name is required.")
    if len(normalized) > 80:
        raise ValidationError("Workspace name must be 80 characters or fewer.")
    return normalized


def workspace_name_key(name: str) -> str:
    return normalize_workspace_name(name).casefold()


def workspace_id_from_name(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-").lower() or "workspace"
    return f"{slug[:48]}-{uuid4().hex[:8]}"


def _read_manifest() -> list[dict]:
    DATA_DIR.mkdir(exist_ok=True)
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    if not WORKSPACES_MANIFEST.exists():
        return []
    try:
        data = json.loads(WORKSPACES_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("Workspace storage is invalid.") from exc
    workspaces = data.get("workspaces") if isinstance(data, dict) else None
    if not isinstance(workspaces, list):
        raise ValidationError("Workspace storage is invalid.")
    return [workspace for workspace in workspaces if isinstance(workspace, dict)]


def _write_manifest(workspaces: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"workspaces": workspaces}
    WORKSPACES_MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_cli_state() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if not CLI_STATE_FILE.exists():
        return {}
    try:
        data = json.loads(CLI_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_cli_state(state: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CLI_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
