from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.backend.application.services.exceptions import ValidationError
from src.backend.infrastructure.models import utc_now


def required_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"Jira OAuth response is missing {key}.")
    return value


def required_payload(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} is required.")
    return value.strip()


def optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def list_str(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def split_scopes(value: str | None) -> list[str]:
    return [scope for scope in (value or "").split() if scope]


def expires_at(expires_in: Any) -> datetime | None:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return utc_now() + timedelta(seconds=seconds)


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_datetime(value: datetime | None) -> str | None:
    if not isinstance(value, datetime):
        return None
    return as_utc(value).isoformat()


def display_name(value: Any) -> str:
    return str(value.get("displayName") or "") if isinstance(value, dict) else ""


def name_field(value: Any) -> str:
    return str(value.get("name") or "") if isinstance(value, dict) else ""
