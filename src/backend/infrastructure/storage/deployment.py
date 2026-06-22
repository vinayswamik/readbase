from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from src.backend.config.settings import DATA_DIR


class DeploymentMode(str, Enum):
    SAAS = "saas"
    CUSTOMER = "customer"


def deployment_mode() -> DeploymentMode:
    raw = os.getenv("READBASE_DEPLOYMENT_MODE", DeploymentMode.SAAS.value).strip().lower()
    try:
        return DeploymentMode(raw)
    except ValueError:
        return DeploymentMode.SAAS


def org_storage_root() -> Path | None:
    raw = os.getenv("READBASE_ORG_STORAGE_ROOT", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_absolute() else DATA_DIR / path


def scratch_dir() -> Path:
    raw = os.getenv("READBASE_SCRATCH_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        return path if path.is_absolute() else DATA_DIR / path
    return Path("/tmp/readbase-scratch")
