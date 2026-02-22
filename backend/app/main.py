"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import api_router
from app.core.database import engine
from app.models.base import Base

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown."""
    logger.info("Starting News Neutralizer API", env=settings.app_env)

    # Create tables (in dev only — use Alembic migrations in prod)
    if settings.app_debug:
        # Create extension outside transaction
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.commit()
            
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (debug mode)")
        
        # Create HNSW indexes for pgvector similarity search (B4/B5)
        async with engine.connect() as conn:
            from sqlalchemy import text
            # HNSW index on structured_facts.embedding
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_structured_facts_embedding_hnsw
                ON structured_facts
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            # HNSW index on article_cache.embedding_vector
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_article_cache_embedding_hnsw
                ON article_cache
                USING hnsw (embedding_vector vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            await conn.commit()
        logger.info("pgvector HNSW indexes created/verified")

    yield

    logger.info("Shutting down News Neutralizer API")
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="News Neutralizer API",
        description="API for news analysis, bias detection, and neutralization",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router, prefix="/api/v1")

    # Health check (outside /api/v1 prefix for Docker healthcheck)
    @app.get("/health", tags=["System"])
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()
