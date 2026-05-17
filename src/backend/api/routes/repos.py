from __future__ import annotations

from fastapi import APIRouter

from src.backend.api.schemas import ReposResponse
from src.backend.application.services.repo_service import list_repositories

router = APIRouter(tags=["repos"])


@router.get("/repos", response_model=ReposResponse)
def repos() -> dict:
    return {"repos": list_repositories()}
