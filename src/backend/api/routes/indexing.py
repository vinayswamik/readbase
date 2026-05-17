from __future__ import annotations

from fastapi import APIRouter

from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import IndexedRepoResponse, IndexRequest
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.repo_service import index_repository

router = APIRouter(tags=["indexing"])


@router.post("/index", response_model=IndexedRepoResponse)
def index_endpoint(payload: IndexRequest) -> dict:
    try:
        return index_repository(payload.repo_url, refresh=payload.refresh)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
