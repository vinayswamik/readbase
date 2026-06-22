from __future__ import annotations

import os

from src.backend.application.services.auth.config import session_cookie_secure
from src.backend.application.services.auth.oidc import APP_BASE_URL, OidcIdentity
from src.backend.application.services.auth.types import AuthUser, normalize_email_key

# Backward-compatible exports used across connector routes.
SESSION_SECURE_COOKIE = session_cookie_secure()
OAUTH_STATE_TTL_SECONDS = 600

# Legacy alias for tests and any remaining imports.
GoogleIdentity = OidcIdentity


def upsert_authenticated_user(identity: OidcIdentity) -> AuthUser:
    from src.backend.application.services.auth.sessions import upsert_oidc_user

    return upsert_oidc_user(identity)


__all__ = [
    "APP_BASE_URL",
    "AuthUser",
    "GoogleIdentity",
    "OAUTH_STATE_TTL_SECONDS",
    "SESSION_SECURE_COOKIE",
    "normalize_email_key",
    "upsert_authenticated_user",
]
