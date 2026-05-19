import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.backend.application.services import auth_service
from src.backend.infrastructure import database


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.original_url = str(database.engine.url)
        database.configure_database(f"sqlite:///{self.data_dir / 'test.db'}")
        database.Base.metadata.drop_all(bind=database.engine)
        database.init_database(seed_admins=False)

    def tearDown(self):
        database.Base.metadata.drop_all(bind=database.engine)
        database.configure_database(self.original_url)
        self.temp_dir.cleanup()

    def test_bootstrap_admins_from_env(self):
        with patch.object(
            auth_service,
            "READBASE_BOOTSTRAP_ADMIN_EMAILS",
            "Admin@Example.com, second@example.com",
        ):
            auth_service.seed_bootstrap_admins()

        self.assertTrue(auth_service.is_admin_approved("admin@example.com"))
        self.assertTrue(auth_service.is_admin_approved("SECOND@example.com"))
        self.assertFalse(auth_service.is_admin_approved("member@example.com"))

    def test_member_login_role_for_approved_admin(self):
        identity = auth_service.GoogleIdentity(
            user_id="google-1",
            email="admin@example.com",
            name="Admin User",
        )

        user = auth_service.upsert_authenticated_user(identity, role="member")
        token = auth_service.create_access_token(user)
        session = auth_service.parse_access_session(token)

        self.assertIsNotNone(session)
        self.assertEqual(session.user.role, "member")

    def test_admin_login_role_in_session(self):
        identity = auth_service.GoogleIdentity(
            user_id="google-1",
            email="admin@example.com",
            name="Admin User",
        )

        user = auth_service.upsert_authenticated_user(identity, role="admin")
        token = auth_service.create_access_token(user)
        session = auth_service.parse_access_session(token)

        self.assertIsNotNone(session)
        self.assertEqual(session.user.role, "admin")


if __name__ == "__main__":
    unittest.main()
