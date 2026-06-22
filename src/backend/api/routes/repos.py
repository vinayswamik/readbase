from __future__ import annotations

from fastapi import APIRouter, HTTPException

LEGACY_ROUTE_MESSAGE = (
    "This endpoint has been removed. Use workspace-scoped APIs under /api/workspaces/{workspace_id}/ instead."
)

router = APIRouter(tags=["repos"])


@router.get("/repos")
def repos() -> None:
    raise HTTPException(status_code=410, detail=LEGACY_ROUTE_MESSAGE)

