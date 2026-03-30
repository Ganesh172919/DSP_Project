from __future__ import annotations

import base64
import hashlib
import json

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings


def _derive_user_key(user_id: str) -> bytes:
    settings = get_settings()
    material = hashlib.pbkdf2_hmac(
        "sha256",
        settings.biometric_master_key.encode("utf-8"),
        user_id.encode("utf-8"),
        120_000,
        dklen=32,
    )
    return material


def encrypt_template(user_id: str, template: dict) -> tuple[bytes, str]:
    key = _derive_user_key(user_id)
    aes = AESGCM(key)
    nonce = hashlib.sha256(f"{user_id}:{template['version']}".encode("utf-8")).digest()[:12]
    ciphertext = aes.encrypt(nonce, json.dumps(template).encode("utf-8"), None)
    digest = hashlib.sha256(ciphertext).hexdigest()
    wrapped = base64.b64encode(nonce + ciphertext)
    return wrapped, digest


def decrypt_template(user_id: str, payload: bytes) -> dict:
    key = _derive_user_key(user_id)
    blob = base64.b64decode(payload)
    nonce, ciphertext = blob[:12], blob[12:]
    aes = AESGCM(key)
    plaintext = aes.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))

