
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
from typing import List, Optional
import sys

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Required secrets
    TELEGRAM_BOT_TOKEN: str
    DASHBOARD_SECRET_KEY: str
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str  # bcrypt/argon2 hash, not plain

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./db/quantum.db"

    # Sentry / logs
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    # Rate limit
    RATE_LIMIT_PER_MINUTE: int = 60

    # Other settings
    ADMIN_IDS: str = ""  # comma-separated telegram admin IDs
    TIMEZONE: str = "UTC"

    @validator("TELEGRAM_BOT_TOKEN", "DASHBOARD_SECRET_KEY", "ADMIN_PASSWORD_HASH")
    def must_not_be_default(cls, v: str):
        if not v or v.strip() in {"changeme", "password", "secret"}:
            print("FATAL: Weak or empty secret detected in .env", file=sys.stderr)
            raise ValueError("Weak/empty secret")
        return v

settings = Settings()
