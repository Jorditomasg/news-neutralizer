"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = False

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://news_user:changeme_in_production@db:5432/news_neutralizer"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── Encryption (Fernet key for user API keys) ─────────────
    encryption_key: str = "changeme_generate_a_real_fernet_key"

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    # ── Rate Limiting ─────────────────────────────────────────
    rate_limit_per_minute: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
