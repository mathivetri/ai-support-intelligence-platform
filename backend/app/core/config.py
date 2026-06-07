"""
core/config.py — Centralised settings for the AI Support Intelligence Platform.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────

    APP_NAME: str = Field(default="AI Support Intelligence Platform")

    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development"
    )

    DEBUG: bool = Field(default=False)

    # ── Database ───────────────────────────────────────────────────────────

    DATABASE_URL: PostgresDsn = Field(...)

    DB_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=5)

    # ── Security / JWT ─────────────────────────────────────────────────────

    SECRET_KEY: str = Field(..., min_length=32)

    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)

    # ── CORS ───────────────────────────────────────────────────────────────
    # Declared as str so pydantic-settings never attempts JSON pre-parsing.
    # The `allowed_origins` property below converts it to list[str] for use.

    ALLOWED_ORIGINS_RAW: str = Field(
        default="http://localhost:3000",
        alias="ALLOWED_ORIGINS",          # reads ALLOWED_ORIGINS from .env
    )

    @computed_field  # type: ignore[misc]
    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        """
        Parse ALLOWED_ORIGINS from .env into a list[str].
        Accepts both formats:
          - Comma-separated : http://localhost:3000,http://localhost:5173
          - JSON array      : ["http://localhost:3000","http://localhost:5173"]
        """
        value = self.ALLOWED_ORIGINS_RAW.strip()
        if value.startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    # ── OpenAI ─────────────────────────────────────────────────────────────

    OPENAI_API_KEY: str = Field(...)
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_MAX_TOKENS: int = Field(default=512, ge=64, le=4096)

    # ── Computed helpers ───────────────────────────────────────────────────

    @computed_field  # type: ignore[misc]
    @property
    def ACCESS_TOKEN_EXPIRE_SECONDS(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @computed_field  # type: ignore[misc]
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    # ── Cross-field validation ─────────────────────────────────────────────

    @model_validator(mode="after")
    def _production_guard(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production.")
            if self.SECRET_KEY in {"changeme", "secret", "your-secret-key"}:
                raise ValueError(
                    "SECRET_KEY looks like a placeholder. "
                    "Generate a real value with: "
                    "python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            insecure = [
                o for o in self.ALLOWED_ORIGINS
                if "localhost" in o or "127.0.0.1" in o
            ]
            if insecure:
                raise ValueError(
                    f"ALLOWED_ORIGINS contains local addresses in production: {insecure}"
                )
        return self


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()