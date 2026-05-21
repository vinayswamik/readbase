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

from .constants import LINEAR_GRAPHQL_URL

TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def linear_graphql_request(query: str, token: str, variables: dict | None = None) -> dict:
    payload = {"query": query, "variables": variables or {}}
    response = json_request(LINEAR_GRAPHQL_URL, method="POST", token=token, body=payload)
    if isinstance(response, dict) and response.get("errors"):
        raise ValidationError(f"Linear GraphQL error: {str(response.get('errors'))[:500]}")
    return response.get("data", {}) if isinstance(response, dict) else {}


def json_request(url: str, method: str = "GET", token: str | None = None, body: dict | None = None) -> Any:
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
            raise PermissionDeniedError("Linear access denied.") from exc
        if exc.code == 404:
            raise ResourceNotFoundError("Linear resource not found.") from exc
        raise ValidationError(f"Linear API returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"Linear API request failed: {exc.reason}") from exc


def linear_form_request(url: str, body: dict[str, str]) -> Any:
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
        raise ValidationError(f"Linear OAuth returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"Linear OAuth request failed: {exc.reason}") from exc


def linear_client_id() -> str:
    value = os.getenv("LINEAR_CLIENT_ID", "").strip()
    if not value:
        raise ValidationError("LINEAR_CLIENT_ID is not configured.")
    return value


def linear_client_secret() -> str:
    value = os.getenv("LINEAR_CLIENT_SECRET", "").strip()
    if not value:
        raise ValidationError("LINEAR_CLIENT_SECRET is not configured.")
    return value


def is_linear_configured() -> bool:
    return bool(os.getenv("LINEAR_CLIENT_ID", "").strip() and os.getenv("LINEAR_CLIENT_SECRET", "").strip())
