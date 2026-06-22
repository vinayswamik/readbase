from __future__ import annotations

import os


def session_cookie_secure() -> bool:
    if os.getenv("APP_ENV", "").strip().lower() == "production":
        return True
    base_url = os.getenv("APP_BASE_URL", "").strip().lower()
    if base_url.startswith("https://"):
        return True
    mode = os.getenv("READBASE_DEPLOYMENT_MODE", "saas").strip().lower()
    if mode == "customer":
        return True
    return os.getenv("APP_SESSION_COOKIE_SECURE", "false").strip().lower() == "true"


def require_production_secrets() -> bool:
    if os.getenv("READBASE_DEPLOYMENT_MODE", "saas").strip().lower() == "customer":
        return True
    if os.getenv("APP_ENV", "").strip().lower() == "production":
        return True
    return os.getenv("READBASE_REQUIRE_PRODUCTION_SECRETS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def validate_auth_secrets() -> None:
    from src.backend.application.services.exceptions import ValidationError

    if not require_production_secrets():
        return
    session_secret = os.getenv("APP_SESSION_SECRET") or os.getenv("READBASE_SESSION_SECRET", "")
    if not session_secret or session_secret == "readbase-dev-session-secret":
        raise ValidationError("APP_SESSION_SECRET is required in customer/production mode.")
    token_key = os.getenv("READBASE_TOKEN_ENCRYPTION_KEY", "").strip()
    if not token_key or token_key == "readbase-dev-token-encryption-key":
        raise ValidationError("READBASE_TOKEN_ENCRYPTION_KEY is required in customer/production mode.")
