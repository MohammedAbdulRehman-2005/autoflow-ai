"""
AutoFlow AI X — App-wide configuration loaded from environment variables.
Uses pydantic-settings for type-safe, validated config.
"""

from functools import lru_cache
from pydantic import field_validator, model_validator
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
    GEMINI_API_KEY: str = ""

    # ── Authentication & Cryptography ─────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15       # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7           # 7 days
    FERNET_KEY: str = ""
    ENCRYPTION_KEY: str = ""

    # ── Feature Flags & Containment ───────────────────────────────────────────
    UNSAFE_EVAL_ENABLED: bool = False
    ALLOW_INSECURE_HTTP: bool = False

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        # Harmonize FERNET_KEY and ENCRYPTION_KEY aliases
        if not self.FERNET_KEY and self.ENCRYPTION_KEY:
            self.FERNET_KEY = self.ENCRYPTION_KEY
        elif not self.ENCRYPTION_KEY and self.FERNET_KEY:
            self.ENCRYPTION_KEY = self.FERNET_KEY

        env_lower = self.ENVIRONMENT.lower()
        if env_lower in ("production", "prod", "release"):
            # 1. Reject default or weak JWT secrets in production
            default_pattern = "change-me-in-production"
            if (
                not self.JWT_SECRET_KEY
                or default_pattern in self.JWT_SECRET_KEY
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError(
                    "Production deployment requires a cryptographically secure JWT_SECRET_KEY "
                    "of at least 32 characters. Do not use default or placeholder keys."
                )

            # 2. Reject missing encryption keys in production
            if not self.FERNET_KEY:
                raise ValueError(
                    "Production deployment requires FERNET_KEY or ENCRYPTION_KEY to be configured "
                    "for OAuth credential protection."
                )

            # 3. Disallow unsafe eval in production
            if self.UNSAFE_EVAL_ENABLED:
                raise ValueError("UNSAFE_EVAL_ENABLED cannot be enabled in production environments.")

        return self

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
