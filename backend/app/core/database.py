"""Database engine, session management, and request dependencies."""

from collections.abc import AsyncGenerator

from fastapi import Header

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


from app.core.security import decode_access_token
from fastapi import HTTPException
import jwt
import structlog

logger = structlog.get_logger()

def get_session_id(x_session_id: str = Header(default="", alias="X-Session-ID")) -> str:
    """Extract and validate session ID from JWT in X-Session-ID header."""
    if not x_session_id or x_session_id == "default":
        # Missing or default header -> anonymous session fallback for health checks or SSR
        return "default"
    
    try:
        # We expect x_session_id to be a valid JWT
        payload = decode_access_token(x_session_id)
        session_id: str | None = payload.get("sub")
        if not session_id:
            raise HTTPException(status_code=401, detail="Invalid session token: missing subject")
        return session_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please reload the page.")
    except jwt.PyJWTError as e:
        logger.warning("Invalid JWT received", token=x_session_id, error=str(e))
        raise HTTPException(status_code=401, detail="Invalid session token")
