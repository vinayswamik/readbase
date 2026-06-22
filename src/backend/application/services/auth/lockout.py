from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass

LOCKOUT_WINDOW_SECONDS = int(os.getenv("APP_AUTH_LOCKOUT_WINDOW_SECONDS", "900"))
LOCKOUT_MAX_FAILURES = int(os.getenv("APP_AUTH_LOCKOUT_MAX_FAILURES", "5"))
LOCKOUT_BASE_SECONDS = int(os.getenv("APP_AUTH_LOCKOUT_BASE_SECONDS", "60"))
LOCKOUT_MAX_SECONDS = int(os.getenv("APP_AUTH_LOCKOUT_MAX_SECONDS", "3600"))


@dataclass
class _FailureRecord:
    timestamps: list[float]
    locked_until: float = 0.0


_records: dict[str, _FailureRecord] = defaultdict(lambda: _FailureRecord(timestamps=[]))


def is_auth_locked(client_key: str) -> tuple[bool, int]:
    record = _records[client_key]
    now = time.time()
    if record.locked_until > now:
        return True, max(1, int(record.locked_until - now))
    if record.locked_until and record.locked_until <= now:
        record.locked_until = 0.0
    return False, 0


def record_auth_failure(client_key: str) -> tuple[bool, int]:
    now = time.time()
    record = _records[client_key]
    window_start = now - LOCKOUT_WINDOW_SECONDS
    record.timestamps = [stamp for stamp in record.timestamps if stamp >= window_start]
    record.timestamps.append(now)

    if len(record.timestamps) < LOCKOUT_MAX_FAILURES:
        return False, 0

    overflow = len(record.timestamps) - LOCKOUT_MAX_FAILURES
    lock_seconds = min(
        LOCKOUT_MAX_SECONDS,
        LOCKOUT_BASE_SECONDS * (2**overflow),
    )
    record.locked_until = now + lock_seconds
    return True, lock_seconds


def record_auth_success(client_key: str) -> None:
    if client_key in _records:
        del _records[client_key]


def reset_auth_lockout() -> None:
    _records.clear()
