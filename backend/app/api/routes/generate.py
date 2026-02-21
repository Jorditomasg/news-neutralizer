"""API routes for generating news from analyzed articles."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.domain import Article, ArticleStatus, GeneratedNews, FactTraceability
from app.api.routes.search import _get_user_ai_config
from app.tasks.generate_tasks import generate_news_from_articles
from app.schemas.schemas import PaginatedGeneratedNewsOut, GeneratedNewsDetailOut
from pydantic import BaseModel, Field

router = APIRouter()

class GenerateRequest(BaseModel):
    article_ids: List[int] = Field(..., min_length=1, description="List of ANALYZED article IDs to base the news on")

class GenerateResponse(BaseModel):
    task_id: str
    message: str = "Generation task started"

@router.post("/", response_model=GenerateResponse)
async def generate_news(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a Celery task to synthethize neutral news from validated facts."""
    
    # 1. Validate all articles exist and are ANALYZED
    stmt = select(Article).where(Article.id.in_(request.article_ids))
    result = await db.execute(stmt)
    articles = result.scalars().all()
    
    if len(articles) != len(request.article_ids):
        raise HTTPException(status_code=404, detail="One or more articles not found")
        
    for auth in articles:
        if auth.status != ArticleStatus.ANALYZED:
            raise HTTPException(status_code=400, detail=f"Article {auth.id} is not fully ANALYZED yet (status: {auth.status})")

    # 2. Get AI config
    provider_name, encrypted_key = await _get_user_ai_config(db)
    
    # 3. Dispatch Celery task
    task = generate_news_from_articles.delay(
        request.article_ids,
        provider_name=provider_name,
        encrypted_api_key=encrypted_key
    )
    
    return GenerateResponse(task_id=task.id)

@router.get("/{news_id}", response_model=GeneratedNewsDetailOut)
async def get_generated_news(
    news_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a generated news article and its traceability links."""
    from sqlalchemy.orm import selectinload
    stmt = select(GeneratedNews).options(
        selectinload(GeneratedNews.traces).selectinload(FactTraceability.structured_fact)
    ).where(GeneratedNews.id == news_id)
    
    result = await db.execute(stmt)
    news = result.scalar_one_or_none()
    
    if not news:
        raise HTTPException(status_code=404, detail="Generated news not found")
        
    # Fetch original articles to display sources
    if news.context_articles_ids:
        art_stmt = select(Article).where(Article.id.in_(news.context_articles_ids))
        art_result = await db.execute(art_stmt)
        news.source_articles = list(art_result.scalars().all())
    else:
        news.source_articles = []
        
    return news

@router.get("/", response_model=PaginatedGeneratedNewsOut)
async def list_generated_news(
    page: int = 1,
    page_size: int = 15,
    db: AsyncSession = Depends(get_db),
):
    """List paginated generated news."""
    from sqlalchemy import func
    
    # Count total
    total_query = select(func.count(GeneratedNews.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()

    # Get items
    offset = (page - 1) * page_size
    stmt = (
        select(GeneratedNews)
        .order_by(GeneratedNews.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PaginatedGeneratedNewsOut(
        total=total,
        page=page,
        page_size=page_size,
        items=list(items)
    )
