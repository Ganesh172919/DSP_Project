from app.core.config import Settings
from app.core.security import hash_password, verify_password


def test_hash_password_supports_long_inputs():
    password = "correct horse battery staple " * 5

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong password", hashed) is False


def test_settings_accepts_comma_separated_cors_origins(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost",
    )

    settings = Settings()

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
    ]
