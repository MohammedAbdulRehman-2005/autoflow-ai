"""
AutoFlow AI X — App-wide configuration loaded from environment variables.
Uses pydantic-settings for type-safe, validated config.
"""

from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "AutoFlow AI X"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: str | bool) -> bool:
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("false", "0", "no", "off", "release", "prod", "production"):
                return False
            if v_lower in ("true", "1", "yes", "on"):
                return True
            return False
        return bool(v)

    SENTRY_DSN: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:5173,https://autoflow-ai-ebon.vercel.app"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str 

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str 

    # ── External APIs / AI ────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15       # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7           # 7 days
    FERNET_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once at startup)."""
    return Settings()
