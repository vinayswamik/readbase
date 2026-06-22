from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.backend.api.routes.repos import LEGACY_ROUTE_MESSAGE

router = APIRouter(tags=["indexing"])


@router.post("/index")
def index_endpoint() -> None:
    raise HTTPException(status_code=410, detail=LEGACY_ROUTE_MESSAGE)

