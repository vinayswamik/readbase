from __future__ import annotations

import logging
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict
from typing import Any

logger = logging.getLogger("readbase.security")

ANOMALY_WINDOW_SECONDS = int(os.getenv("APP_SECURITY_ANOMALY_WINDOW_SECONDS", "300"))
ANOMALY_THRESHOLDS: dict[str, int] = {
    "auth_login_failed": int(os.getenv("APP_SECURITY_ANOMALY_AUTH_LOGIN_FAILED", "10")),
    "auth_session_invalid": int(os.getenv("APP_SECURITY_ANOMALY_AUTH_SESSION_INVALID", "20")),
    "workspace_access_denied": int(os.getenv("APP_SECURITY_ANOMALY_WORKSPACE_DENIED", "30")),
    "csrf_rejected": int(os.getenv("APP_SECURITY_ANOMALY_CSRF_REJECTED", "15")),
}
_event_buckets: dict[str, list[float]] = defaultdict(list)


def record_security_event(event_type: str, **fields: Any) -> None:
    payload = {"event_type": event_type, **fields}
    logger.info("security_event %s", payload)
    _track_anomaly(event_type, payload)


def _track_anomaly(event_type: str, payload: dict[str, Any]) -> None:
    threshold = ANOMALY_THRESHOLDS.get(event_type)
    if threshold is None:
        return
    now = time.time()
    window_start = now - ANOMALY_WINDOW_SECONDS
    bucket = _event_buckets[event_type]
    bucket[:] = [stamp for stamp in bucket if stamp >= window_start]
    bucket.append(now)
    if len(bucket) < threshold:
        return
    anomaly = {
        "event_type": "security_anomaly",
        "anomaly_type": event_type,
        "count": len(bucket),
        "window_seconds": ANOMALY_WINDOW_SECONDS,
        "threshold": threshold,
        **{key: value for key, value in payload.items() if key != "event_type"},
    }
    logger.error("security_anomaly %s", anomaly)
    webhook = os.getenv("APP_SECURITY_WEBHOOK_URL", "").strip()
    if webhook:
        _post_security_webhook(webhook, anomaly)


def _post_security_webhook(url: str, payload: dict[str, Any]) -> None:
    import json

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status >= 400:
                logger.warning("security_anomaly webhook returned HTTP %s", response.status)
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("security_anomaly webhook failed: %s", exc)


def reset_security_anomaly_tracking() -> None:
    _event_buckets.clear()
