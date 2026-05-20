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


def jira_request(
    cloud_id: str,
    path: str,
    token: str,
    method: str = "GET",
    query: dict[str, str] | None = None,
    body: dict | None = None,
) -> Any:
    quoted_cloud = urllib.parse.quote(cloud_id)
    url = f"https://api.atlassian.com/ex/jira/{quoted_cloud}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    return json_request(url, method=method, token=token, body=body)


def json_request(url: str, method: str = "GET", token: str | None = None, body: dict | None = None) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
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
            raise PermissionDeniedError("Jira access denied.") from exc
        if exc.code == 404:
            raise ResourceNotFoundError("Jira resource not found.") from exc
        raise ValidationError(f"Jira API returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"Jira API request failed: {exc.reason}") from exc


def safe_json_request(url: str, token: str) -> Any:
    try:
        return json_request(url, token=token)
    except Exception:
        return None


def jira_client_id() -> str:
    value = os.getenv("JIRA_CLIENT_ID", "").strip()
    if not value:
        raise ValidationError("JIRA_CLIENT_ID is not configured.")
    return value


def jira_client_secret() -> str:
    value = os.getenv("JIRA_CLIENT_SECRET", "").strip()
    if not value:
        raise ValidationError("JIRA_CLIENT_SECRET is not configured.")
    return value
