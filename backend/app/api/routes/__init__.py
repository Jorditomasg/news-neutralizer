"""API route aggregation."""

from fastapi import APIRouter

from app.api.routes.search import router as search_router
from app.api.routes.articles import router as articles_router
from app.api.routes.settings import router as settings_router
from app.api.routes.sources import router as sources_router
from app.api.routes.websocket import router as ws_router
from app.api.routes.history import router as history_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.generate import router as generate_router

api_router = APIRouter()

api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(articles_router, prefix="/articles", tags=["Articles"])
api_router.include_router(settings_router, prefix="/settings", tags=["Settings"])
api_router.include_router(sources_router, prefix="/sources", tags=["Sources"])
api_router.include_router(history_router, prefix="/history", tags=["History"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(generate_router, prefix="/generate", tags=["Generated News"])
api_router.include_router(ws_router, tags=["WebSocket"])
