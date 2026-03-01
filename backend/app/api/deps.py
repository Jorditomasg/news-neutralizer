"""API dependencies."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserAPIKey

async def _get_user_ai_config(db: AsyncSession, session_id: str = "default") -> tuple[str, str | None]:
    """Get the user's preferred AI provider and encrypted key."""
    stmt = select(UserAPIKey).where(UserAPIKey.session_id == session_id, UserAPIKey.is_valid == True)
    result = await db.execute(stmt)
    keys = result.scalars().all()

    # Priority: openai > anthropic > google > ollama
    for provider_name in ["openai", "anthropic", "google", "ollama"]:
        for key in keys:
            if key.provider == provider_name:
                return provider_name, key.encrypted_key

    # No keys configured — default to ollama (no key needed)
    return "ollama", None
