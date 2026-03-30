from app.services.biometric_crypto import decrypt_template, encrypt_template


def test_template_roundtrip_encryption():
    template = {"version": 1, "quality_score": 82.5, "steps": {"front": {"embedding": [0.1, 0.2]}}}
    ciphertext, digest = encrypt_template("user-123", template)
    restored = decrypt_template("user-123", ciphertext)
    assert restored == template
    assert len(digest) == 64

