from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.api.auth import require_authenticated_user
from src.backend.api.errors import service_error_to_http
from src.backend.api.schemas import NotificationsResponse
from src.backend.application.services.exceptions import ServiceError
from src.backend.application.services.notification_service import list_notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsResponse)
def list_notifications_endpoint(user=Depends(require_authenticated_user)) -> dict:
    try:
        return list_notifications(user.user_id)
    except ServiceError as exc:
        raise service_error_to_http(exc) from exc
