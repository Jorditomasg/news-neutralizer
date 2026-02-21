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
