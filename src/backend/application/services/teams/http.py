from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import certifi

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError

TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def teams_json_request(path: str, token: str) -> Any:
    request = urllib.request.Request(
        f"https://graph.microsoft.com/v1.0{path}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}", "User-Agent": "readbase"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30, context=TLS_CONTEXT) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        if exc.code in {401, 403}:
            raise PermissionDeniedError("Microsoft Teams access denied.") from exc
        if exc.code == 404:
            raise ResourceNotFoundError("Microsoft Teams resource not found.") from exc
        raise ValidationError(f"Microsoft Graph returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"Microsoft Graph request failed: {exc.reason}") from exc


def teams_form_request(url: str, body: dict[str, str]) -> Any:
    data = urllib.parse.urlencode(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "readbase"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30, context=TLS_CONTEXT) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValidationError(f"Microsoft OAuth returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"Microsoft OAuth request failed: {exc.reason}") from exc


def microsoft_client_id() -> str:
    value = os.getenv("MICROSOFT_CLIENT_ID", "").strip()
    if not value:
        raise ValidationError("MICROSOFT_CLIENT_ID is not configured.")
    return value


def microsoft_client_secret() -> str:
    value = os.getenv("MICROSOFT_CLIENT_SECRET", "").strip()
    if not value:
        raise ValidationError("MICROSOFT_CLIENT_SECRET is not configured.")
    return value


def is_teams_configured() -> bool:
    return bool(os.getenv("MICROSOFT_CLIENT_ID", "").strip() and os.getenv("MICROSOFT_CLIENT_SECRET", "").strip())
