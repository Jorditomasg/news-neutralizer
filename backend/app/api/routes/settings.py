"""Settings endpoints: API key management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_session_id
from app.core.security import encrypt_api_key
from app.models import UserAPIKey
from app.schemas import APIKeyCreate, APIKeyOut

router = APIRouter()


@router.post("/api-keys", response_model=APIKeyOut)
async def save_api_key(
    request: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """Save or update a user's API key (encrypted at rest)."""

    # Find if the key already exists for this provider
    stmt = select(UserAPIKey).where(
        UserAPIKey.session_id == session_id,
        UserAPIKey.provider == request.provider,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    # Enforce a single provider per session: delete keys for other providers
    delete_others_stmt = select(UserAPIKey).where(
        UserAPIKey.session_id == session_id,
        UserAPIKey.provider != request.provider,
    )
    others_result = await db.execute(delete_others_stmt)
    for other_key in others_result.scalars().all():
        await db.delete(other_key)

    encrypted = encrypt_api_key(request.api_key)

    if existing:
        existing.encrypted_key = encrypted
        existing.is_valid = True
    else:
        existing = UserAPIKey(
            session_id=session_id,
            provider=request.provider,
            encrypted_key=encrypted,
        )
        db.add(existing)

    await db.flush()

    return APIKeyOut(
        provider=existing.provider,
        is_valid=existing.is_valid,
        created_at=existing.created_at,
    )


@router.get("/api-keys", response_model=list[APIKeyOut])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """List configured API keys (never returns the actual key values)."""

    stmt = select(UserAPIKey).where(UserAPIKey.session_id == session_id)
    result = await db.execute(stmt)
    keys = result.scalars().all()

    return [
        APIKeyOut(provider=k.provider, is_valid=k.is_valid, created_at=k.created_at)
        for k in keys
    ]


@router.delete("/api-keys/{provider}")
async def delete_api_key(
    provider: str,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """Delete a user's API key."""

    stmt = select(UserAPIKey).where(
        UserAPIKey.session_id == session_id,
        UserAPIKey.provider == provider,
    )
    result = await db.execute(stmt)
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(key)
    return {"message": f"API key for {provider} deleted"}
