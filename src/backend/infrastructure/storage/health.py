from __future__ import annotations

from pathlib import Path

from src.backend.infrastructure.storage.deployment import DeploymentMode, deployment_mode, org_storage_root, scratch_dir
from src.backend.infrastructure.storage.resolver import resolve_cli_storage_context


def check_storage_health() -> dict:
    mode = deployment_mode()
    cli_context = resolve_cli_storage_context()
    checks: dict[str, dict] = {
        "deployment_mode": {"ok": True, "value": mode.value},
        "cli_data_dir": _writable_check(cli_context.workspace_root),
        "scratch_dir": _writable_check(scratch_dir()),
    }

    if mode is DeploymentMode.CUSTOMER:
        root = org_storage_root()
        checks["org_storage_root"] = (
            _writable_check(root) if root is not None else {"ok": False, "error": "READBASE_ORG_STORAGE_ROOT is not set"}
        )

    ok = all(item.get("ok") for item in checks.values())
    return {"ok": ok, "checks": checks}


def _writable_check(path: Path) -> dict:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".readbase-health"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"ok": True, "path": str(path)}
    except OSError as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}
