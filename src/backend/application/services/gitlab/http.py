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

from .constants import GITLAB_API_URL

TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def gitlab_json_request(path_or_url: str, token: str | None = None, method: str = "GET", body: dict | None = None) -> Any:
    url = path_or_url if path_or_url.startswith("https://") else f"{GITLAB_API_URL}{path_or_url}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "User-Agent": "readbase"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30, context=TLS_CONTEXT) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        if exc.code in {401, 403}:
            raise PermissionDeniedError("GitLab access denied.") from exc
        if exc.code == 404:
            raise ResourceNotFoundError("GitLab project not found.") from exc
        raise ValidationError(f"GitLab API returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"GitLab API request failed: {exc.reason}") from exc


def gitlab_form_request(url: str, body: dict[str, str]) -> Any:
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
        raise ValidationError(f"GitLab OAuth returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"GitLab OAuth request failed: {exc.reason}") from exc


def gitlab_client_id() -> str:
    value = os.getenv("GITLAB_CLIENT_ID", "").strip()
    if not value:
        raise ValidationError("GITLAB_CLIENT_ID is not configured.")
    return value


def gitlab_client_secret() -> str:
    value = os.getenv("GITLAB_CLIENT_SECRET", "").strip()
    if not value:
        raise ValidationError("GITLAB_CLIENT_SECRET is not configured.")
    return value


def is_gitlab_configured() -> bool:
    return bool(os.getenv("GITLAB_CLIENT_ID", "").strip() and os.getenv("GITLAB_CLIENT_SECRET", "").strip())
