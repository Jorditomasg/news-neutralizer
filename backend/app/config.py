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
    encryption_key: str = "TjQ5cEVIblpYV1lZTEpKZ09DdUQxaVptc1ZqT203eXc="

    # ── JWT Authentication ────────────────────────────────────
    secret_key: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    access_token_expire_minutes: int = 43200  # 30 days

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    # ── Rate Limiting ─────────────────────────────────────────
    rate_limit_per_minute: int = 30
    
    # ── Topic Analysis ────────────────────────────────────────
    topic_cache_ttl_days: int = 60

    # ── Ollama ────────────────────────────────────────────────
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1"

    @property
    def sync_database_url(self) -> str:
        """Convert async DB URL to sync for Celery workers."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
