"""
crypto.py — AES-256-GCM encryption/decryption for face embedding vectors.
Also handles JWT RS256 key generation and token creation/verification.
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import jwt, JWTError
from pathlib import Path

from app.config import (
    AES_KEY, JWT_PRIVATE_KEY_PATH, JWT_PUBLIC_KEY_PATH,
    JWT_ALGORITHM, JWT_EXPIRY_MINUTES, BASE_DIR,
)


# ═══════════════════════════════════════════════════════════════════════════
# AES-256-GCM  — Embedding Encryption
# ═══════════════════════════════════════════════════════════════════════════

def _get_aes_key() -> bytes:
    """Derive 32-byte key from hex-encoded env var."""
    raw = bytes.fromhex(AES_KEY)
    if len(raw) != 32:
        raise ValueError(
            f"AES key must be 256 bits (32 bytes). Got {len(raw)} bytes. "
            "Set FACE_AUTH_AES_KEY env var to a 64-char hex string."
        )
    return raw


def encrypt_embedding(embedding: np.ndarray) -> bytes:
    """
    Encrypt a 512-d float32 embedding vector with AES-256-GCM.
    Returns: nonce (12 bytes) || ciphertext+tag
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce recommended for GCM
    plaintext = embedding.astype(np.float32).tobytes()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_embedding(encrypted: bytes) -> np.ndarray:
    """
    Decrypt an AES-256-GCM encrypted embedding back to 512-d float32 vector.
    Input format: nonce (12 bytes) || ciphertext+tag
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return np.frombuffer(plaintext, dtype=np.float32).copy()


# ═══════════════════════════════════════════════════════════════════════════
# JWT RS256  — Token Management
# ═══════════════════════════════════════════════════════════════════════════

def _ensure_rsa_keys():
    """Generate RSA-2048 key pair if they don't exist."""
    priv_path = Path(JWT_PRIVATE_KEY_PATH)
    pub_path = Path(JWT_PUBLIC_KEY_PATH)

    if priv_path.exists() and pub_path.exists():
        return

    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    priv_path.parent.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Write private key
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_path.write_bytes(priv_pem)

    # Write public key
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path.write_bytes(pub_pem)


def create_jwt(user_id: str, username: str) -> str:
    """Create RS256 JWT token with 15-minute expiry."""
    _ensure_rsa_keys()
    private_key = Path(JWT_PRIVATE_KEY_PATH).read_text()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRY_MINUTES),
        "iss": "face-auth-system",
    }
    return jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> dict:
    """Verify and decode RS256 JWT. Raises JWTError on failure."""
    _ensure_rsa_keys()
    public_key = Path(JWT_PUBLIC_KEY_PATH).read_text()
    return jwt.decode(token, public_key, algorithms=[JWT_ALGORITHM])
