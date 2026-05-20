from __future__ import annotations

import base64
import hashlib
import hmac
import os

from src.backend.application.services.auth_service import SESSION_SECRET
from src.backend.application.services.exceptions import PermissionDeniedError


def encrypt_token(value: str) -> str:
    key = token_key()
    nonce = os.urandom(16)
    plaintext = value.encode("utf-8")
    stream = keystream(key, nonce, len(plaintext))
    ciphertext = bytes(left ^ right for left, right in zip(plaintext, stream))
    mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + mac + ciphertext).decode("ascii")


def decrypt_token(value: str) -> str:
    raw = base64.urlsafe_b64decode(value.encode("ascii"))
    nonce, mac, ciphertext = raw[:16], raw[16:48], raw[48:]
    key = token_key()
    expected = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise PermissionDeniedError("Stored Jira token could not be decrypted.")
    stream = keystream(key, nonce, len(ciphertext))
    return bytes(left ^ right for left, right in zip(ciphertext, stream)).decode("utf-8")


def keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < length:
        output.extend(hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(output[:length])


def token_key() -> bytes:
    secret = os.getenv("READBASE_TOKEN_ENCRYPTION_KEY") or SESSION_SECRET
    return hashlib.sha256(secret.encode("utf-8")).digest()
