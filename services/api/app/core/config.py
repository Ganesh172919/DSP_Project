from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    cors_origins: Annotated[
        List[str],
        NoDecode,
    ] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost"])
    access_token_expire_minutes: int = 15

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
