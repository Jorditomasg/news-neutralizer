"""WebSocket endpoint for real-time task progress updates."""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models import SearchTask

router = APIRouter()


from app.core.redis_utils import get_expected_duration
from app.api.deps import _get_user_ai_config

@router.websocket("/ws/tasks/{task_id}")
async def task_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket that sends task progress updates every 2 seconds.

    Messages format:
    {
        "task_id": "uuid",
        "status": "pending|scraping|analyzing|completed|failed",
        "progress": 0-100,
        "message": "Human-readable status message"
    }
    """
    await websocket.accept()

    try:
        while True:
            async with AsyncSessionLocal() as session:
                stmt = select(SearchTask).where(SearchTask.task_id == task_id).options(selectinload(SearchTask.articles))
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()

                if not task:
                    await websocket.send_json({
                        "task_id": task_id,
                        "status": "not_found",
                        "progress": 0,
                        "message": "Task not found",
                    })
                    break

                # Use specific progress message from DB if available
                db_msg = task.progress_message
                if db_msg and task.status != "failed":
                    message = db_msg
                else:
                    message = task.error_message if task.status == "failed" and task.error_message else _status_message(task.status, task.progress)

                warnings = []
                for a in task.articles:
                    if getattr(a, 'is_truncated', False):
                        warnings.append(
                            f"⚠️ The source {a.source_name} appears to have a paywall. "
                            f"The article might be incomplete and the analysis may not be reliable."
                        )
                        break

                provider_name, _ = await _get_user_ai_config(session, "session_id_not_needed_for_ws")
                ema_ms = get_expected_duration(provider_name)

                await websocket.send_json({
                    "task_id": task.task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "progress_message": task.progress_message,
                    "error_message": task.error_message,
                    "message": message,
                    "warnings": warnings,
                    "expected_duration_ms": ema_ms,
                })

                # Stop polling if task is done
                if task.status in ("completed", "failed"):
                    break

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        pass


def _status_message(status: str, progress: int) -> str:
    """Generate a human-readable status message."""
    messages = {
        "pending": "Starting search...",
        "scraping": "Extracting articles...",
        "analyzing": "Analyzing bias with AI...",
        "completed": "✅ Analysis completed",
        "failed": "❌ Analysis error",
        "preview": "Article preview",
    }
    return messages.get(status, f"Status: {status}")
