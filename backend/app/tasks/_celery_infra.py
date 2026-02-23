"""Shared infrastructure for all Celery task modules.

Provides a single synchronous SQLAlchemy engine/session and helpers
so that every task file reuses the same connection pool and async bridge.

Celery forks worker processes — asyncpg connections can NOT be shared
across forks. We use psycopg2 (sync) for all DB access in tasks.
"""

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.security import decrypt_api_key
from app.services.ai.factory import AIProviderFactory

# ── Single synchronous engine for ALL Celery workers ──────────
sync_engine = create_engine(
    settings.sync_database_url,
    echo=settings.app_debug,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(bind=sync_engine)


def run_async(coro):
    """Run an async coroutine from a synchronous Celery task.

    Always creates a fresh event loop to avoid conflicts with
    Celery's prefork worker model.
    """
    import nest_asyncio
    loop = asyncio.new_event_loop()
    nest_asyncio.apply(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_ai_provider(provider_name: str, encrypted_api_key: str | None, language: str = "es", summary_length: str = "medium", bias_strictness: str = "standard"):
    """Create an AI provider instance, decrypting the API key if provided."""
    api_key = None
    if encrypted_api_key:
        api_key = decrypt_api_key(encrypted_api_key)
    return AIProviderFactory.get(provider_name, api_key=api_key, language=language, summary_length=summary_length, bias_strictness=bias_strictness)
