import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import call, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.api.routes import api_router
from src.backend.api.security_middleware import RATE_LIMITS, RateLimitRule, SecurityMiddleware
from src.backend.application.services.auth.config import validate_auth_secrets
from src.backend.application.services.auth.rate_limit import reset_rate_limits
from src.backend.application.services.auth.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, generate_csrf_token
from src.backend.application.services.auth.oidc import OidcIdentity
from src.backend.application.services.auth.sessions import (
    SESSION_COOKIE_NAME,
    create_user_session,
    refresh_user_session,
    resolve_session_user,
    revoke_user_session,
)
from src.backend.application.services import auth_service
from src.backend.application.services.exceptions import ValidationError
from src.backend.application.services.security.token_vault import decrypt_secret, encrypt_secret
from src.backend.infrastructure import database
from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import UserSession


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database()
        self.app = FastAPI()
        self.app.add_middleware(SecurityMiddleware)
        self.app.include_router(api_router)
        self.client = TestClient(self.app)
        from src.backend.application.services.auth.lockout import reset_auth_lockout
        from src.backend.application.services.auth.oauth_codes import reset_oauth_codes
        from src.backend.application.services.auth.rate_limit import reset_rate_limits
        from src.backend.application.services.auth.security_events import reset_security_anomaly_tracking

        reset_auth_lockout()
        reset_oauth_codes()
        reset_security_anomaly_tracking()
        reset_rate_limits()

    def tearDown(self):
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_login_persists_user_and_session(self):
        identity = OidcIdentity(
            user_id="oidc-1",
            email="user@example.com",
            name="Regular User",
        )

        user = auth_service.upsert_authenticated_user(identity)
        session_token, _expires_at = create_user_session(user)
        resolved = resolve_session_user(session_token)

        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.user.user_id, "oidc-1")
        self.assertEqual(resolved.user.email, "user@example.com")
        self.assertEqual(resolved.user.name, "Regular User")
        self.assertEqual(
            user.to_dict(),
            {
                "id": "oidc-1",
                "email": "user@example.com",
                "name": "Regular User",
            },
        )

    def test_session_revocation_invalidates_token(self):
        identity = OidcIdentity(user_id="oidc-2", email="revoke@example.com", name="Revoke User")
        user = auth_service.upsert_authenticated_user(identity)
        session_token, _expires_at = create_user_session(user)
        revoke_user_session(session_token)
        self.assertIsNone(resolve_session_user(session_token))

    def test_token_vault_round_trip(self):
        ciphertext = encrypt_secret("provider-access-token")
        self.assertEqual(decrypt_secret(ciphertext), "provider-access-token")

    def test_session_rotation_returns_new_expiry(self):
        identity = OidcIdentity(user_id="oidc-3", email="rotate@example.com", name="Rotate User")
        user = auth_service.upsert_authenticated_user(identity)
        with (
            patch("src.backend.application.services.auth.sessions.SESSION_TTL_SECONDS", 3600),
            patch("src.backend.application.services.auth.sessions.SESSION_REFRESH_WINDOW_SECONDS", 7200),
        ):
            session_token, old_expires = create_user_session(user)
            rotated = refresh_user_session(session_token)
        self.assertIsNotNone(rotated)
        new_token, new_expires = rotated
        self.assertNotEqual(new_token, session_token)
        self.assertGreater(new_expires, old_expires)
        self.assertIsNone(resolve_session_user(session_token))
        self.assertIsNotNone(resolve_session_user(new_token))

    def test_expired_session_returns_401_at_http_layer(self):
        identity = OidcIdentity(user_id="oidc-4", email="expired@example.com", name="Expired User")
        user = auth_service.upsert_authenticated_user(identity)
        session_token, _expires_at = create_user_session(user)
        from src.backend.application.services.auth.sessions import _hash_token
        from sqlalchemy import select

        token_hash = _hash_token(session_token)
        with session_scope() as session:
            record = session.scalar(select(UserSession).where(UserSession.session_token_hash == token_hash))
            record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=30)

        self.client.cookies.set(SESSION_COOKIE_NAME, session_token)
        response = self.client.get("/api/workspaces")
        self.assertEqual(response.status_code, 401)

    def test_oauth_state_tampering_rejected(self):
        response = self.client.get(
            "/api/auth/callback?code=fake-code&state=tampered",
            cookies={"readbase_oauth_state": "expected-state"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("auth_error=invalid_state", response.headers["location"])

    def test_rate_limit_returns_429(self):
        limited_rules = {"/api/auth/logout": RateLimitRule(2, 60)}
        with patch.dict("src.backend.api.security_middleware.RATE_LIMITS", limited_rules, clear=True):
            reset_rate_limits()
            self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
            self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
            response = self.client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 429)

    def test_session_rotation_sets_correct_cookie_expiry(self):
        identity = OidcIdentity(user_id="oidc-5", email="cookie@example.com", name="Cookie User")
        user = auth_service.upsert_authenticated_user(identity)
        with (
            patch("src.backend.application.services.auth.sessions.SESSION_TTL_SECONDS", 3600),
            patch("src.backend.application.services.auth.sessions.SESSION_REFRESH_WINDOW_SECONDS", 7200),
        ):
            session_token, _expires_at = create_user_session(user)
            self.client.cookies.set(SESSION_COOKIE_NAME, session_token)
            response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, 200)
        set_cookie = response.headers.get("set-cookie", "")
        max_age_match = re.search(r"Max-Age=(\d+)", set_cookie)
        self.assertIsNotNone(max_age_match)
        self.assertGreater(int(max_age_match.group(1)), 3000)

    def test_production_secret_validation_fails_startup(self):
        env = {
            "APP_ENV": "production",
            "APP_SESSION_SECRET": "readbase-dev-session-secret",
            "READBASE_TOKEN_ENCRYPTION_KEY": "readbase-dev-token-encryption-key",
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(ValidationError):
                validate_auth_secrets()

    def test_csrf_mutating_request_without_token_returns_403(self):
        identity = OidcIdentity(user_id="oidc-6", email="csrf@example.com", name="CSRF User")
        user = auth_service.upsert_authenticated_user(identity)
        session_token, _expires_at = create_user_session(user)
        csrf_token = generate_csrf_token()
        self.client.cookies.set(SESSION_COOKIE_NAME, session_token)
        self.client.cookies.set(CSRF_COOKIE_NAME, csrf_token)

        blocked = self.client.post("/api/workspaces", json={"name": "Secure"})
        self.assertEqual(blocked.status_code, 403)

        allowed = self.client.post(
            "/api/workspaces",
            json={"name": "Secure"},
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.json()["owner_user_id"], user.user_id)

    def test_logout_clears_session_and_returns_401(self):
        identity = OidcIdentity(user_id="oidc-7", email="logout@example.com", name="Logout User")
        user = auth_service.upsert_authenticated_user(identity)
        session_token, _expires_at = create_user_session(user)
        csrf_token = generate_csrf_token()
        self.client.cookies.set(SESSION_COOKIE_NAME, session_token)
        self.client.cookies.set(CSRF_COOKIE_NAME, csrf_token)

        logout_response = self.client.post(
            "/api/auth/logout",
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(self.client.get("/api/workspaces").status_code, 401)

    def test_revoked_session_returns_401_at_http_layer(self):
        identity = OidcIdentity(user_id="oidc-8", email="revoked@example.com", name="Revoked User")
        user = auth_service.upsert_authenticated_user(identity)
        session_token, _expires_at = create_user_session(user)
        revoke_user_session(session_token)
        self.client.cookies.set(SESSION_COOKIE_NAME, session_token)
        self.assertEqual(self.client.get("/api/workspaces").status_code, 401)

    def test_oauth_code_replay_rejected(self):
        from src.backend.application.services.auth.oauth_codes import consume_oauth_code, reset_oauth_codes

        reset_oauth_codes()
        self.assertTrue(consume_oauth_code("code-once"))
        self.assertFalse(consume_oauth_code("code-once"))

    def test_exchange_oidc_code_rejects_replayed_authorization_code(self):
        from src.backend.application.services.auth.oauth_codes import reset_oauth_codes

        reset_oauth_codes()
        with (
            patch("src.backend.application.services.auth.oidc.load_oidc_config") as load_config,
            patch("src.backend.application.services.auth.oidc._exchange_code_for_tokens") as exchange_tokens,
            patch("src.backend.application.services.auth.oidc._verify_id_token") as verify_token,
        ):
            load_config.return_value = type("Cfg", (), {"client_id": "client", "provider_name": "test"})()
            exchange_tokens.return_value = {"id_token": "token"}
            verify_token.return_value = {
                "sub": "oidc-9",
                "email": "replay@example.com",
                "name": "Replay User",
            }
            from src.backend.application.services.auth.oidc import exchange_oidc_code

            exchange_oidc_code("shared-code", "verifier", "nonce")
            with self.assertRaises(ValidationError):
                exchange_oidc_code("shared-code", "verifier", "nonce")

    def test_auth_lockout_after_repeated_failures(self):
        from src.backend.application.services.auth.lockout import reset_auth_lockout

        reset_auth_lockout()
        with (
            patch("src.backend.application.services.auth.lockout.LOCKOUT_MAX_FAILURES", 2),
            patch("src.backend.application.services.auth.lockout.LOCKOUT_BASE_SECONDS", 30),
        ):
            for _ in range(2):
                response = self.client.get(
                    "/api/auth/callback?code=fake&state=bad",
                    cookies={"readbase_oauth_state": "expected"},
                    follow_redirects=False,
                )
                self.assertEqual(response.status_code, 303)
            blocked = self.client.get(
                "/api/auth/callback?code=fake&state=bad",
                cookies={"readbase_oauth_state": "expected"},
                follow_redirects=False,
            )
        self.assertEqual(blocked.status_code, 429)

    def test_security_anomaly_logged_on_threshold(self):
        from src.backend.application.services.auth.security_events import (
            record_security_event,
            reset_security_anomaly_tracking,
        )

        reset_security_anomaly_tracking()
        with (
            patch("src.backend.application.services.auth.security_events.ANOMALY_THRESHOLDS", {"auth_login_failed": 3}),
            patch("src.backend.application.services.auth.security_events.logger") as security_logger,
        ):
            for _ in range(3):
                record_security_event("auth_login_failed", reason="test")
        anomaly_calls = [
            call
            for call in security_logger.error.call_args_list
            if call.args and call.args[0] == "security_anomaly %s"
        ]
        self.assertTrue(anomaly_calls)

    def test_idle_session_returns_401_at_http_layer(self):
        identity = OidcIdentity(user_id="oidc-11", email="idle@example.com", name="Idle User")
        user = auth_service.upsert_authenticated_user(identity)
        session_token, _expires_at = create_user_session(user)
        from src.backend.application.services.auth.sessions import _hash_token
        from sqlalchemy import select

        token_hash = _hash_token(session_token)
        with session_scope() as session:
            record = session.scalar(select(UserSession).where(UserSession.session_token_hash == token_hash))
            record.last_used_at = datetime.now(timezone.utc) - timedelta(seconds=120)

        with patch("src.backend.application.services.auth.sessions.SESSION_IDLE_TIMEOUT_SECONDS", 60):
            self.client.cookies.set(SESSION_COOKIE_NAME, session_token)
            response = self.client.get("/api/workspaces")
        self.assertEqual(response.status_code, 401)

    def test_session_endpoint_issues_csrf_cookie_when_missing(self):
        identity = OidcIdentity(user_id="oidc-10", email="csrf-session@example.com", name="CSRF Session")
        user = auth_service.upsert_authenticated_user(identity)
        session_token, _expires_at = create_user_session(user)
        self.client.cookies.set(SESSION_COOKIE_NAME, session_token)

        response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, 200)
        self.assertIn(CSRF_COOKIE_NAME, response.headers.get("set-cookie", ""))


if __name__ == "__main__":
    unittest.main()
