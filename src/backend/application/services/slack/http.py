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

from .constants import SLACK_API_URL

TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class SlackRateLimitError(ValidationError):
    def __init__(self, retry_after_seconds: int = 60):
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__(f"Slack rate limited this request. Retry after {self.retry_after_seconds} seconds.")


def slack_api_request(path: str, token: str | None = None, method: str = "GET", query: dict | None = None, body: dict | None = None) -> Any:
    url = path if path.startswith("https://") else f"{SLACK_API_URL}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    data = urllib.parse.urlencode(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "User-Agent": "readbase"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30, context=TLS_CONTEXT) as response:
            payload = parse_json(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise SlackRateLimitError(retry_after(exc)) from exc
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValidationError(f"Slack API returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"Slack API request failed: {exc.reason}") from exc
    validate_slack_payload(payload)
    return payload


def slack_oauth_request(body: dict[str, str]) -> Any:
    return slack_api_request("/oauth.v2.access", method="POST", body=body)


def validate_slack_payload(payload: Any) -> None:
    if not isinstance(payload, dict) or payload.get("ok", True):
        return
    error = str(payload.get("error") or "unknown_error")
    if error in {"not_authed", "invalid_auth", "account_inactive", "token_revoked", "token_expired", "missing_scope", "no_permission", "not_in_channel"}:
        raise PermissionDeniedError(f"Slack access denied: {error}.")
    if error in {"channel_not_found", "team_not_found"}:
        raise ResourceNotFoundError(f"Slack resource not found: {error}.")
    if error == "ratelimited":
        raise SlackRateLimitError()
    raise ValidationError(f"Slack API error: {error}.")


def parse_json(raw: str) -> Any:
    return json.loads(raw) if raw else {}


def retry_after(exc: urllib.error.HTTPError) -> int:
    try:
        return int(exc.headers.get("Retry-After") or "60")
    except ValueError:
        return 60


def slack_client_id() -> str:
    value = os.getenv("SLACK_CLIENT_ID", "").strip()
    if not value:
        raise ValidationError("SLACK_CLIENT_ID is not configured.")
    return value


def slack_client_secret() -> str:
    value = os.getenv("SLACK_CLIENT_SECRET", "").strip()
    if not value:
        raise ValidationError("SLACK_CLIENT_SECRET is not configured.")
    return value


def is_slack_configured() -> bool:
    return bool(os.getenv("SLACK_CLIENT_ID", "").strip() and os.getenv("SLACK_CLIENT_SECRET", "").strip())
