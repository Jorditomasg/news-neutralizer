"""API routes for the user feedback system."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, get_session_id
from app.models.domain import Feedback, SearchTask
from app.schemas.schemas import FeedbackCreate
from app.tasks.feedback_tasks import process_feedback_async

router = APIRouter()

@router.post("/")
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """
    Submit user feedback for an analysis, an article, or a domain.
    The system asynchronously processes this feedback to adjust heuristics and trust scores.
    """
    # Simply record the feedback in the DB
    feedback_entry = Feedback(
        target_type=payload.target_type,
        target_id=payload.target_id,
        vote=payload.vote,
        session_id=session_id
    )
    
    db.add(feedback_entry)
    await db.commit()
    await db.refresh(feedback_entry)
    
    # Trigger background task to process the feedback
    process_feedback_async.delay(feedback_entry.id)
    
    return {"status": "success", "message": "Feedback recorded and queued for processing", "feedback_id": feedback_entry.id}
