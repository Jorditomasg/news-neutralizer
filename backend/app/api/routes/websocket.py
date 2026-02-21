"""WebSocket endpoint for real-time task progress updates."""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import SearchTask

router = APIRouter()


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
                stmt = select(SearchTask).where(SearchTask.task_id == task_id)
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()

                if not task:
                    await websocket.send_json({
                        "task_id": task_id,
                        "status": "not_found",
                        "progress": 0,
                        "message": "Tarea no encontrada",
                    })
                    break

                # Use specific progress message from DB if available
                db_msg = task.progress_message
                if db_msg and task.status != "failed":
                    message = db_msg
                else:
                    message = task.error_message if task.status == "failed" and task.error_message else _status_message(task.status, task.progress)

                await websocket.send_json({
                    "task_id": task.task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "progress_message": task.progress_message,
                    "error_message": task.error_message,
                    "message": message,
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
        "pending": "Iniciando búsqueda...",
        "scraping": "Extrayendo artículos",
        "analyzing": "Analizando sesgo con IA",
        "completed": "✅ Análisis completado",
        "failed": "❌ Error en el análisis",
        "preview": "Vista previa del artículo",
    }
    return messages.get(status, f"Estado: {status}")
