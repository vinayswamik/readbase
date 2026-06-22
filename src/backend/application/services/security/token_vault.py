from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.backend.application.services.auth.config import require_production_secrets
from src.backend.application.services.exceptions import PermissionDeniedError, ValidationError

VAULT_VERSION = "v1"
DEFAULT_KEY_VERSION = "k1"
NONCE_BYTES = 12


@dataclass(frozen=True)
class VaultRecord:
    version: str
    key_version: str
    nonce: str
    ciphertext: str


def encrypt_secret(value: str) -> str:
    key_version, key = _active_key()
    nonce = os.urandom(NONCE_BYTES)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
    record = VaultRecord(
        version=VAULT_VERSION,
        key_version=key_version,
        nonce=base64.urlsafe_b64encode(nonce).decode("ascii"),
        ciphertext=base64.urlsafe_b64encode(ciphertext).decode("ascii"),
    )
    return _encode_record(record)


def decrypt_secret(value: str) -> str:
    if _looks_like_legacy_token(value):
        return _decrypt_legacy_token(value)
    record = _decode_record(value)
    if record.version != VAULT_VERSION:
        raise PermissionDeniedError("Unsupported token vault version.")
    key = _key_for_version(record.key_version)
    nonce = base64.urlsafe_b64decode(f"{record.nonce}{'=' * (-len(record.nonce) % 4)}")
    ciphertext = base64.urlsafe_b64decode(f"{record.ciphertext}{'=' * (-len(record.ciphertext) % 4)}")
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as exc:
        raise PermissionDeniedError("Stored token could not be decrypted.") from exc
    return plaintext.decode("utf-8")


def migrate_legacy_secret(value: str) -> str:
    plaintext = _decrypt_legacy_token(value)
    return encrypt_secret(plaintext)


def _active_key() -> tuple[str, bytes]:
    key_version = os.getenv("READBASE_TOKEN_KEY_VERSION", DEFAULT_KEY_VERSION).strip() or DEFAULT_KEY_VERSION
    return key_version, _key_for_version(key_version)


def _key_for_version(key_version: str) -> bytes:
    env_name = f"READBASE_TOKEN_ENCRYPTION_KEY_{key_version.upper()}"
    raw = os.getenv(env_name, "").strip()
    if not raw:
        raw = os.getenv("READBASE_TOKEN_ENCRYPTION_KEY", "").strip()
    if not raw:
        if require_production_secrets():
            raise ValidationError("READBASE_TOKEN_ENCRYPTION_KEY is required in customer/production mode.")
        raw = "readbase-dev-token-encryption-key"
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return digest


def _encode_record(record: VaultRecord) -> str:
    payload = {
        "v": record.version,
        "kv": record.key_version,
        "n": record.nonce,
        "c": record.ciphertext,
    }
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _decode_record(value: str) -> VaultRecord:
    try:
        padding = "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(f"{value}{padding}")
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PermissionDeniedError("Stored token format is invalid.") from exc
    if not isinstance(payload, dict):
        raise PermissionDeniedError("Stored token format is invalid.")
    return VaultRecord(
        version=str(payload.get("v", "")),
        key_version=str(payload.get("kv", "")),
        nonce=str(payload.get("n", "")),
        ciphertext=str(payload.get("c", "")),
    )


def _looks_like_legacy_token(value: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(f"{value}{'=' * (-len(value) % 4)}")
    except Exception:
        return False
    return len(raw) >= 48 and not value.startswith("ey")


def _decrypt_legacy_token(value: str) -> str:
    raw = base64.urlsafe_b64decode(f"{value}{'=' * (-len(value) % 4)}")
    nonce, mac, ciphertext = raw[:16], raw[16:48], raw[48:]
    key = _legacy_key()
    expected = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise PermissionDeniedError("Stored token could not be decrypted.")
    stream = _legacy_keystream(key, nonce, len(ciphertext))
    return bytes(left ^ right for left, right in zip(ciphertext, stream)).decode("utf-8")


def _legacy_key() -> bytes:
    raw = os.getenv("READBASE_TOKEN_ENCRYPTION_KEY", "").strip()
    if not raw:
        session_secret = os.getenv("APP_SESSION_SECRET") or os.getenv("READBASE_SESSION_SECRET") or "readbase-dev-session-secret"
        raw = session_secret
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _legacy_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < length:
        output.extend(hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(output[:length])
