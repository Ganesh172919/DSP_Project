from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DeepShield Guardian API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./guardian.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "development-secret-key"
    biometric_master_key: str = "0123456789abcdef0123456789abcdef"
    face_service_url: str | None = None
    risk_service_url: str | None = None
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost"])
    access_token_expire_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()

