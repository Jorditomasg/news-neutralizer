"""News sources configuration endpoint."""

from fastapi import APIRouter

from app.schemas import AvailableSource
from app.services.scraper.sources import AVAILABLE_SOURCES

router = APIRouter()


@router.get("/", response_model=list[AvailableSource])
async def list_sources():
    """List all available news sources."""
    return AVAILABLE_SOURCES
