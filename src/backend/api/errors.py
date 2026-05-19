from __future__ import annotations

from fastapi import HTTPException

from src.backend.application.services.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)


def service_error_to_http(error: ServiceError) -> HTTPException:
    if isinstance(error, ResourceNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, PermissionDeniedError):
        return HTTPException(status_code=403, detail=str(error))
    if isinstance(error, ValidationError):
        return HTTPException(status_code=400, detail=str(error))
    return HTTPException(status_code=500, detail="Unexpected service error.")
