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
import math

router = APIRouter()

from app.api.deps import _get_user_ai_config
from app.core.rate_limit import limiter
from app.config import settings

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
        return {"is_specific": False, "reason": "Please provide more context (use at least 3 words) or select a specific news article."}

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
from app.core.redis_utils import get_expected_duration

@router.post("/", response_model=TaskCreated)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def search_news(
    body: SearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """
    Unified search: auto-detects URL vs topic query.
    - URL input -> extract article, generate semantic query, search related articles
    - Text input -> search RSS feeds by keywords
    """
    task_id = str(uuid.uuid4())
    is_url_input = _is_url(body.query)

    # Extract user preferences from headers
    language = request.headers.get("Accept-Language", "es")
    summary_length = request.headers.get("X-Summary-Length", "medium")
    bias_strictness = request.headers.get("X-Bias-Strictness", "standard")

    # Create search task record
    search_task = SearchTask(
        task_id=task_id,
        session_id=session_id,
        query=body.query if not is_url_input else None,
        source_url=body.query if is_url_input else None,
        status="pending",
    )
    db.add(search_task)
    await db.commit()

    # Get AI config
    provider_name, encrypted_key = await _get_user_ai_config(db)

    if is_url_input:
        target_url = body.query.strip()
        
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
                ema_ms = get_expected_duration(provider_name)
                return TaskCreated(task_id=old_task.task_id, expected_duration_ms=ema_ms)

        # URL mode: extract -> semantic query -> search -> analyze
        search_and_analyze_url.delay(
            task_id=task_id,
            url=target_url,
            original_query=body.original_query,
            source_slugs=body.sources,
            provider_name=provider_name,
            encrypted_api_key=encrypted_key,
            language=language,
            summary_length=summary_length,
            bias_strictness=bias_strictness,
        )
    else:
        # Topic mode: Fast heuristic + cache check (non-blocking)
        rejection = await _check_topic_specificity_fast(db, body.query)
        
        if rejection and not rejection.get("is_specific", True):
            from fastapi import HTTPException
            reason = rejection.get("reason", "Topic is too generic or ambiguous.")
            raise HTTPException(status_code=400, detail=f"AMBIGUOUS_TOPIC: {reason}")

        # Specific enough (or needs LLM check in worker) -> search RSS -> analyze
        search_and_analyze.delay(
            task_id=task_id,
            query=body.query,
            source_slugs=body.sources,
            provider_name=provider_name,
            encrypted_api_key=encrypted_key,
            language=language,
            summary_length=summary_length,
            bias_strictness=bias_strictness,
        )

    ema_ms = get_expected_duration(provider_name)
    return TaskCreated(task_id=task_id, expected_duration_ms=ema_ms)


@router.post("/headlines", response_model=list[ArticlePreviewResponse])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def search_headlines(
    body: SearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Search for headlines (without starting full analysis).
    Used for the "Disambiguation" step in frontend.
    """
    from app.services.scraper.google_news import search_google_news_rss
    
    language = request.headers.get("Accept-Language", "es")
    hits = await search_google_news_rss(body.query, max_results=10, language=language)
    
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
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def preview_article(body: ExtractArticleRequest, request: Request):
    """
    Extract article metadata from a URL for preview.
    Does not save to DB or start analysis.
    """
    extractor = ArticleExtractor()
    extracted = await extractor.extract(str(body.url))
    
    return ArticlePreviewResponse(
        title=extracted.title,
        source_name=extracted.source_name,
        source_url=extracted.source_url,
        author=extracted.author,
        published_at=extracted.published_at,
        topics=extracted.topics,
        image_url=extracted.image_url,
        body=extracted.body,
    )


@router.get("/stats/average-time")
async def get_average_analysis_time(db: AsyncSession = Depends(get_db)):
    """Get the global average analysis time based on recent tasks, rounded up to nearest 15s."""
    stmt = (
        select(SearchTask.created_at, SearchTask.completed_at)
        .where(
            SearchTask.status == 'completed',
            SearchTask.completed_at != None,
            SearchTask.created_at != None
        )
        .order_by(SearchTask.completed_at.desc())
        .limit(100)
    )
    
    result = await db.execute(stmt)
    rows = result.fetchall()
    
    if not rows:
        return {"average_time_ms": 255000} # default 60s
        
    total_seconds = 0
    count = 0
    for created_at, completed_at in rows:
        diff = (completed_at - created_at).total_seconds()
        if diff > 0 and diff < 600: # sanity check: ignore negative or super long (>10m) tasks
            total_seconds += diff
            count += 1
            
    if count == 0:
        return {"average_time_ms": 255000}
        
    avg_seconds = total_seconds / count
    
    # We want to round it up to the nearest 15 seconds. e.g. 62 -> 75
    rounded_seconds = math.ceil(avg_seconds / 15.0) * 15
    rounded_seconds = max(15, rounded_seconds)
    
    return {"average_time_ms": int(rounded_seconds * 1000)}


@router.get("/{task_id}")
@limiter.limit("60/minute") # allow faster polling for status checks
async def get_search_results(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
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
                f"⚠️ The source {a.source_name} appears to have a paywall. "
                f"The article might be incomplete and the analysis may not be reliable."
            )
            break  # one warning per task is enough

    provider_name, _ = await _get_user_ai_config(db, session_id)
    ema_ms = get_expected_duration(provider_name)

    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "query": task.query,
        "source_url": task.source_url,
        "source_article": source_article,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "articles": articles_out,
        "analysis": analysis_out,
        "error_message": task.error_message,
        "warnings": warnings,
        "expected_duration_ms": ema_ms,
    }
