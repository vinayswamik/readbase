from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.api.auth import require_authenticated_user
from src.backend.api.schemas import ReposResponse
from src.backend.application.services.repo_service import list_repositories

router = APIRouter(tags=["repos"])


@router.get("/repos", response_model=ReposResponse)
def repos(_user=Depends(require_authenticated_user)) -> dict:
    return {"repos": list_repositories()}
