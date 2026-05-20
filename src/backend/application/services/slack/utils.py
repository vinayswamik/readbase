from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.backend.application.services.exceptions import ValidationError


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def required_payload(payload: dict, key: str) -> str:
    value = optional_str(payload.get(key))
    if not value:
        raise ValidationError(f"{key} is required.")
    return value


def bool_payload(payload: dict, key: str) -> bool:
    return bool(payload.get(key))


def list_scopes(value: str) -> list[str]:
    return [scope for scope in value.replace(",", " ").split() if scope]


def slack_ts_to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
