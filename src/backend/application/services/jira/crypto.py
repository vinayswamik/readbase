from __future__ import annotations

from src.backend.application.services.security.token_vault import decrypt_secret, encrypt_secret

encrypt_token = encrypt_secret
decrypt_token = decrypt_secret

__all__ = ["decrypt_token", "encrypt_token"]
