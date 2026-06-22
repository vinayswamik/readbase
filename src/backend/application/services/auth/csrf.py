from __future__ import annotations

import secrets

from src.backend.application.services.auth.config import session_cookie_secure

CSRF_COOKIE_NAME = "readbase_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_tokens_match(header_value: str | None, cookie_value: str | None) -> bool:
    if header_value is None or cookie_value is None:
        return False
    return secrets.compare_digest(header_value, cookie_value)


def set_csrf_cookie(response, csrf_token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=2592000,
        httponly=False,
        samesite="lax",
        secure=session_cookie_secure(),
        path="/",
    )


def clear_csrf_cookie(response) -> None:
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")
