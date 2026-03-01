"""Authentication routes for JWT session issuance."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.security import create_access_token
from app.config import settings

router = APIRouter()

class SessionRequest(BaseModel):
    # If the user has an old raw UUID session_id, they can exchange it for a JWT once.
    # We trust it because there were no accounts previously, so any UUID is just their workspace.
    old_session_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/session", response_model=TokenResponse)
async def create_session(request: SessionRequest = None):
    """
    Generate an anonymous JWT session token.
    If an old_session_id is provided, the JWT will encode that ID
    so the user doesn't lose their history or API keys. 
    """
    session_id = None
    if request and request.old_session_id:
        # Very loose validation to avoid generating massive tokens
        if len(request.old_session_id) > 100:
            raise HTTPException(status_code=400, detail="Invalid old session ID length")
        session_id = request.old_session_id
    else:
        session_id = str(uuid.uuid4())
        
    # The JWT payload encodes the sub as the user's session identifier
    access_token = create_access_token(data={"sub": session_id})
    return TokenResponse(access_token=access_token)
