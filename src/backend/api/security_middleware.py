from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.backend.application.services.auth.config import session_cookie_secure
from src.backend.application.services.auth.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    csrf_tokens_match,
)
from src.backend.application.services.auth.lockout import is_auth_locked
from src.backend.application.services.auth.rate_limit import RateLimitRule, allow_rate_limit
from src.backend.application.services.auth.security_events import record_security_event
from src.backend.application.services.auth.sessions import SESSION_COOKIE_NAME
from src.backend.infrastructure.storage.deployment import DeploymentMode, deployment_mode


RATE_LIMITS: dict[str, RateLimitRule] = {
    "/api/auth/start": RateLimitRule(30, 60),
    "/api/auth/callback": RateLimitRule(30, 60),
    "/api/auth/google/start": RateLimitRule(30, 60),
    "/api/auth/google/callback": RateLimitRule(30, 60),
    "/api/auth/logout": RateLimitRule(60, 60),
    "/api/auth/session": RateLimitRule(120, 60),
}
INVITE_JOIN_RATE_LIMIT = RateLimitRule(40, 60)


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        if _is_auth_callback_path(path):
            locked, retry_after = is_auth_locked(client_ip)
            if locked:
                record_security_event("auth_login_failed", reason="lockout", client_ip=client_ip)
                return Response(
                    status_code=429,
                    content="Too many failed login attempts. Try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

        rule = RATE_LIMITS.get(path)
        if rule is not None:
            bucket_key = f"{client_ip}:{path}"
            if not allow_rate_limit(bucket_key, rule):
                return Response(status_code=429, content="Too many requests.")

        if path.startswith("/api/invites/join/"):
            bucket_key = f"{client_ip}:invite-join"
            if not allow_rate_limit(bucket_key, INVITE_JOIN_RATE_LIMIT):
                return Response(status_code=429, content="Too many invite preview requests.")

        if path.startswith("/api/me/integrations/") and (
            path.endswith("/start") or path.endswith("/callback")
        ):
            bucket_key = f"{client_ip}:connector-oauth"
            connector_rule = RateLimitRule(40, 60)
            if not allow_rate_limit(bucket_key, connector_rule):
                return Response(status_code=429, content="Too many connector OAuth requests.")

        if _requires_csrf_protection(request):
            session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
            if session_cookie:
                csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
                csrf_header = request.headers.get(CSRF_HEADER_NAME)
                if not csrf_tokens_match(csrf_header, csrf_cookie):
                    record_security_event("csrf_rejected", path=path, client_ip=client_ip)
                    return Response(status_code=403, content="CSRF token missing or invalid.")

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if deployment_mode() == DeploymentMode.CUSTOMER or session_cookie_secure():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response


def _requires_csrf_protection(request: Request) -> bool:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return False
    path = request.url.path
    if not path.startswith("/api/"):
        return False
    if path.endswith("/callback"):
        return False
    return True


def _is_auth_callback_path(path: str) -> bool:
    return path in {"/api/auth/callback", "/api/auth/google/callback"}
