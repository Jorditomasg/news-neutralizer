"""Search endpoints: topic search and cross-reference."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import SearchTask, UserAPIKey
from app.schemas import SearchRequest, TaskCreated, ExtractArticleRequest, ArticlePreviewResponse
from app.tasks.search_tasks import search_and_analyze, search_and_analyze_url
from app.services.scraper import ArticleExtractor


router = APIRouter()


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


def _is_url(text: str) -> bool:
    """Check if the input looks like a URL."""
    t = text.strip()
    return t.startswith("http://") or t.startswith("https://")


@router.post("/", response_model=TaskCreated)
async def search_news(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Unified search: auto-detects URL vs topic query.
    - URL input -> extract article, generate semantic query, search related articles
    - Text input -> search RSS feeds by keywords
    """
    task_id = str(uuid.uuid4())
    is_url_input = _is_url(request.query)

    # Create search task record
    search_task = SearchTask(
        task_id=task_id,
        session_id="default",
        query=request.query if not is_url_input else None,
        source_url=request.query if is_url_input else None,
        status="pending",
    )
    db.add(search_task)
    await db.commit()

    # Get AI config
    provider_name, encrypted_key = await _get_user_ai_config(db)

    if is_url_input:
        # URL mode: extract -> semantic query -> search -> analyze
        search_and_analyze_url.delay(
            task_id=task_id,
            url=request.query.strip(),
            source_slugs=request.sources,
            provider_name=provider_name,
            encrypted_api_key=encrypted_key,
        )
    else:
        # Topic mode: search RSS -> analyze
        search_and_analyze.delay(
            task_id=task_id,
            query=request.query,
            source_slugs=request.sources,
            provider_name=provider_name,
            encrypted_api_key=encrypted_key,
        )

    return TaskCreated(task_id=task_id)


    return TaskCreated(task_id=task_id)


@router.post("/headlines", response_model=list[ArticlePreviewResponse])
async def search_headlines(request: SearchRequest):
    """
    Search for headlines (without starting full analysis).
    Used for the "Disambiguation" step in frontend.
    """
    # Import here to avoid circular imports
    from app.services.scraper.google_news import search_google_news_rss
    
    hits = await search_google_news_rss(request.query, max_results=10)
    
    return [
        ArticlePreviewResponse(
            title=hit.title,
            source_name=hit.source_name,
            source_url=hit.url,
            author=None,
            published_at=None, # Google News RSS date format needs parsing if we want it here
            topics=[],
        )
        for hit in hits
    ]


@router.post("/preview", response_model=ArticlePreviewResponse)
async def preview_article(request: ExtractArticleRequest):
    """
    Extract article metadata from a URL for preview.
    Does not save to DB or start analysis.
    """
    extractor = ArticleExtractor()
    extracted = await extractor.extract(str(request.url))
    
    return ArticlePreviewResponse(
        title=extracted.title,
        source_name=extracted.source_name,
        source_url=extracted.source_url,
        author=extracted.author,
        published_at=extracted.published_at,
        topics=extracted.topics,
    )


@router.get("/{task_id}")
async def get_search_results(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the status and results of a search task."""
    stmt = (
        select(SearchTask)
        .where(SearchTask.task_id == task_id)
        .options(
            selectinload(SearchTask.articles),
            selectinload(SearchTask.analysis),
        )
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")

    # Build response manually to handle ORM -> dict conversion
    articles_out = [
        {
            "id": a.id,
            "title": a.title,
            "source_name": a.source_name,
            "source_url": a.source_url,
            "author": a.author,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "body": a.body,
            "bias_score": a.bias_score,
            "bias_details": a.bias_details,
            "cluster_id": a.cluster_id,
            "is_source": a.is_source,
        }
        for a in task.articles
    ]

    # Extract the source article info (if URL-based search)
    source_article = None
    for a in task.articles:
        if a.is_source:
            source_article = {
                "title": a.title,
                "source_name": a.source_name,
                "source_url": a.source_url,
            }
            break

    analysis_out = None
    if task.analysis:
        analysis_out = {
            "topic_summary": task.analysis.topic_summary,
            "objective_facts": task.analysis.objective_facts,
            "bias_elements": task.analysis.bias_elements,
            "neutralized_summary": task.analysis.neutralized_summary,
            "source_bias_scores": task.analysis.source_bias_scores,
            "provider_used": task.analysis.provider_used,
            "tokens_used": task.analysis.tokens_used,
        }

    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "query": task.query,
        "source_url": task.source_url,
        "source_article": source_article,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "articles": articles_out,
        "analysis": analysis_out,
        "error_message": task.error_message,
    }
