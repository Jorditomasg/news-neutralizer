"""Article extraction endpoint (direct URL input)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Article, SearchTask
from app.schemas import ArticlePreview, ExtractArticleRequest
from app.services.scraper.extractor import ArticleExtractor

router = APIRouter()

_extractor = ArticleExtractor()


@router.post("/extract", response_model=ArticlePreview)
async def extract_article(
    request: ExtractArticleRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Extract article content from a URL.
    Returns a preview for the user to validate before cross-reference search.
    """
    try:
        extracted = await _extractor.extract(str(request.url))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not extract article: {e}")

    # Create a search task to hold this article
    task_id = str(uuid.uuid4())
    search_task = SearchTask(
        task_id=task_id,
        session_id="default",
        source_url=str(request.url),
        status="preview",
    )
    db.add(search_task)
    await db.flush()

    # Save the extracted article
    article = Article(
        search_task_id=search_task.id,
        source_name=extracted.source_name,
        source_url=str(request.url),
        title=extracted.title,
        body=extracted.body,
        author=extracted.author,
        published_at=extracted.published_at,
    )
    db.add(article)
    await db.flush()

    return ArticlePreview(
        id=article.id,
        title=extracted.title,
        source_name=extracted.source_name,
        source_url=str(request.url),
        author=extracted.author,
        published_at=extracted.published_at,
        body_preview=extracted.body[:500] if extracted.body else "",
        detected_topics=extracted.topics,
    )
