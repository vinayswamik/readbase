from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import AskRequest, AskResponse
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.question_service import ask_repository_question

router = APIRouter(tags=["questions"])


@router.post("/ask", response_model=AskResponse)
def ask_endpoint(payload: AskRequest, _user=Depends(require_authenticated_user)) -> dict:
    try:
        return ask_repository_question(
            repo_id=payload.repo_id,
            question=payload.question,
            top_k=payload.top_k,
        )
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
