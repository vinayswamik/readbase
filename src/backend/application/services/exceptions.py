from __future__ import annotations


class ServiceError(RuntimeError):
    """Base class for errors that should be mapped at the app boundary."""


class ValidationError(ServiceError):
    """Raised when caller input is missing or invalid."""


class ResourceNotFoundError(ServiceError):
    """Raised when a requested local resource does not exist."""


class PermissionDeniedError(ServiceError):
    """Raised when an authenticated caller is not allowed to do something."""
