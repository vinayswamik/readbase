from __future__ import annotations

from fastapi import APIRouter

from src.backend.infrastructure.storage.health import check_storage_health

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/storage")
def storage_health() -> dict:
    return check_storage_health()
