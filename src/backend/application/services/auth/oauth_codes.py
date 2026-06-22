from __future__ import annotations

import time

CODE_TTL_SECONDS = 600
_used_codes: dict[str, float] = {}


def consume_oauth_code(code: str) -> bool:
    """Return True when the code is unused; False on replay."""
    normalized = code.strip()
    if not normalized:
        return False
    _purge_expired()
    if normalized in _used_codes:
        return False
    _used_codes[normalized] = time.time()
    return True


def reset_oauth_codes() -> None:
    _used_codes.clear()


def _purge_expired() -> None:
    now = time.time()
    expired = [code for code, stamp in _used_codes.items() if now - stamp > CODE_TTL_SECONDS]
    for code in expired:
        del _used_codes[code]
