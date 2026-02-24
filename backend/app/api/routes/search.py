"""Search endpoints: topic search and cross-reference."""

import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db, get_session_id
from app.models import SearchTask, UserAPIKey, Article
from app.models.domain import ArticleStatus
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





async def _check_topic_specificity_fast(db: AsyncSession, topic: str) -> dict | None:
    """
    Fast, non-blocking topic validation using heuristics and DB cache only.
    
    Returns a rejection dict if the topic is known to be too broad,
    or None if it passes the fast checks (LLM validation will happen in the Celery task).
    """
    import hashlib
    from datetime import datetime, timedelta, timezone
    from app.models import TopicCache
    from app.config import settings
    
    # 1. Fast Heuristic Filter (instant)
    words = topic.strip().split()
    if len(words) <= 2:
        return {"is_specific": False, "reason": "Por favor, proporciona más contexto (usa al menos 3 palabras) o selecciona una noticia concreta."}

    # 2. Check DB Cache for previously evaluated topics (instant)
    normalized_topic = topic.strip().lower()
    topic_hash = hashlib.sha256(normalized_topic.encode()).hexdigest()
    
    stmt = select(TopicCache).where(TopicCache.topic_hash == topic_hash)
    result = await db.execute(stmt)
    cached = result.scalar_one_or_none()
    
    if cached:
        now = datetime.now(timezone.utc)
        created_at = cached.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
            
        if created_at < now - timedelta(days=settings.topic_cache_ttl_days):
            await db.delete(cached)
            await db.commit()
        elif not cached.is_specific:
            # We know from a previous LLM evaluation that this topic is too broad
            return {"is_specific": False, "reason": cached.reason}
    
    # Passes fast checks — full LLM validation will happen in the Celery task
    return None


from fastapi import Request

@router.post("/", response_model=TaskCreated)
async def search_news(
    request: SearchRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """
    Unified search: auto-detects URL vs topic query.
    - URL input -> extract article, generate semantic query, search related articles
    - Text input -> search RSS feeds by keywords
    """
    task_id = str(uuid.uuid4())
    is_url_input = _is_url(request.query)

    # Extract user preferences from headers
    language = req.headers.get("Accept-Language", "es")
    summary_length = req.headers.get("X-Summary-Length", "medium")
    bias_strictness = req.headers.get("X-Bias-Strictness", "standard")

    # Create search task record
    search_task = SearchTask(
        task_id=task_id,
        session_id=session_id,
        query=request.query if not is_url_input else None,
        source_url=request.query if is_url_input else None,
        status="pending",
    )
    db.add(search_task)
    await db.commit()

    # Get AI config
    provider_name, encrypted_key = await _get_user_ai_config(db)

    if is_url_input:
        target_url = request.query.strip()
        
        # Fast-Track: Check if article is already ANALYZED
        stmt = select(Article).where(Article.source_url == target_url, Article.status == ArticleStatus.ANALYZED)
        result = await db.execute(stmt)
        existing_article = result.scalars().first()
        
        if existing_article:
            # Get the original search task id to redirect there
            old_task_stmt = select(SearchTask).where(SearchTask.id == existing_article.search_task_id)
            old_task_result = await db.execute(old_task_stmt)
            old_task = old_task_result.scalar_one_or_none()
            if old_task:
                return TaskCreated(task_id=old_task.task_id)

        # URL mode: extract -> semantic query -> search -> analyze
        search_and_analyze_url.delay(
            task_id=task_id,
            url=target_url,
            original_query=request.original_query,
            source_slugs=request.sources,
            provider_name=provider_name,
            encrypted_api_key=encrypted_key,
            language=language,
            summary_length=summary_length,
            bias_strictness=bias_strictness,
        )
    else:
        # Topic mode: Fast heuristic + cache check (non-blocking)
        rejection = await _check_topic_specificity_fast(db, request.query)
        
        if rejection and not rejection.get("is_specific", True):
            from fastapi import HTTPException
            reason = rejection.get("reason", "Tema demasiado genérico o ambiguo.")
            raise HTTPException(status_code=400, detail=f"AMBIGUOUS_TOPIC: {reason}")

        # Specific enough (or needs LLM check in worker) -> search RSS -> analyze
        search_and_analyze.delay(
            task_id=task_id,
            query=request.query,
            source_slugs=request.sources,
            provider_name=provider_name,
            encrypted_api_key=encrypted_key,
            language=language,
            summary_length=summary_length,
            bias_strictness=bias_strictness,
        )

    return TaskCreated(task_id=task_id)


@router.post("/headlines", response_model=list[ArticlePreviewResponse])
async def search_headlines(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search for headlines (without starting full analysis).
    Used for the "Disambiguation" step in frontend.
    """
    # Import here to avoid circular imports
    from app.services.scraper.google_news import search_google_news_rss
    
    hits = await search_google_news_rss(request.query, max_results=10)
    
    responses = []
    for hit in hits:
        responses.append(ArticlePreviewResponse(
            title=hit.title,
            source_name=hit.source_name,
            source_url=hit.url,
            author=None,
            published_at=None,
            topics=[],
            has_paywall=False,
        ))
        
    return responses


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
            "status": a.status.value if hasattr(a.status, 'value') else a.status,
            "analyzed_at": a.analyzed_at.isoformat() if a.analyzed_at else None,
            "bias_score": a.bias_score,
            "bias_details": a.bias_details,
            "cluster_id": a.cluster_id,
            "is_source": a.is_source,
            "is_truncated": a.is_truncated,
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
            "neutralized_article": task.analysis.neutralized_article,
            "source_bias_scores": task.analysis.source_bias_scores,
            "provider_used": task.analysis.provider_used,
            "tokens_used": task.analysis.tokens_used,
        }

    # Build warnings list
    from app.models.domain import SourceDomain
    warnings = []
    for a in task.articles:
        if a.is_truncated:
            warnings.append(
                f"⚠️ El medio {a.source_name} parece tener contenido de pago. "
                f"El artículo podría estar incompleto y el análisis podría no ser fiable."
            )
            break  # one warning per task is enough

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
        "warnings": warnings,
    }
