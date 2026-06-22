from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.backend.api.routes.repos import LEGACY_ROUTE_MESSAGE

router = APIRouter(tags=["questions"])


@router.post("/ask")
def ask_endpoint() -> None:
    raise HTTPException(status_code=410, detail=LEGACY_ROUTE_MESSAGE)

