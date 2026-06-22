from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import certifi

from src.backend.application.services.exceptions import PermissionDeniedError, ResourceNotFoundError, ValidationError

from .constants import NOTION_API_BASE, NOTION_API_VERSION

TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def notion_request(path: str, token: str, method: str = "GET", query: dict[str, str] | None = None, body: dict | None = None) -> Any:
    url = f"{NOTION_API_BASE}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    return json_request(url, method=method, token=token, body=body)


def json_request(url: str, method: str = "GET", token: str | None = None, body: dict | None = None, basic_auth: tuple[str, str] | None = None) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "Notion-Version": NOTION_API_VERSION, "User-Agent": "readbase"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if basic_auth:
        encoded = base64.b64encode(f"{basic_auth[0]}:{basic_auth[1]}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {encoded}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30, context=TLS_CONTEXT) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        if exc.code in {401, 403}:
            raise PermissionDeniedError(f"Notion access denied: {detail[:500] or f'HTTP {exc.code}'}") from exc
        if exc.code == 404:
            raise ResourceNotFoundError("Notion resource not found.") from exc
        raise ValidationError(f"Notion API returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"Notion API request failed: {exc.reason}") from exc


def notion_client_id() -> str:
    value = os.getenv("NOTION_CLIENT_ID", "").strip()
    if not value:
        raise ValidationError("NOTION_CLIENT_ID is not configured.")
    return value


def notion_client_secret() -> str:
    value = os.getenv("NOTION_CLIENT_SECRET", "").strip()
    if not value:
        raise ValidationError("NOTION_CLIENT_SECRET is not configured.")
    return value


def is_notion_configured() -> bool:
    return bool(os.getenv("NOTION_CLIENT_ID", "").strip() and os.getenv("NOTION_CLIENT_SECRET", "").strip())
