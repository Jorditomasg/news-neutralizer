"""Search endpoints: topic search and cross-reference."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import SearchTask, UserAPIKey
from app.schemas import CrossReferenceRequest, SearchRequest, TaskCreated
from app.tasks.search_tasks import search_and_analyze, cross_reference_analyze

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


@router.post("/", response_model=TaskCreated)
async def search_news(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search for news articles about a topic.
    Creates an async task that scrapes, clusters, and analyzes articles.
    """
    task_id = str(uuid.uuid4())

    # Create search task record
    search_task = SearchTask(
        task_id=task_id,
        session_id="default",
        query=request.query,
        status="pending",
    )
    db.add(search_task)
    await db.commit()

    # Get AI config
    provider_name, encrypted_key = await _get_user_ai_config(db)

    # Enqueue Celery task
    search_and_analyze.delay(
        task_id=task_id,
        query=request.query,
        source_slugs=request.sources,
        provider_name=provider_name,
        encrypted_api_key=encrypted_key,
    )

    return TaskCreated(task_id=task_id)


@router.post("/cross-reference", response_model=TaskCreated)
async def cross_reference_search(
    request: CrossReferenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search for articles related to a previously extracted article.
    Used after the preview/validation step.
    """
    task_id = str(uuid.uuid4())

    search_task = SearchTask(
        task_id=task_id,
        session_id="default",
        query=" ".join(request.topics),
        status="pending",
    )
    db.add(search_task)
    await db.commit()

    provider_name, encrypted_key = await _get_user_ai_config(db)

    cross_reference_analyze.delay(
        task_id=task_id,
        article_id=request.article_id,
        topics=request.topics,
        source_slugs=request.sources,
        provider_name=provider_name,
        encrypted_api_key=encrypted_key,
    )

    return TaskCreated(task_id=task_id)


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

    # Build response manually to handle ORM → dict conversion
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
        }
        for a in task.articles
    ]

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
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "articles": articles_out,
        "analysis": analysis_out,
        "error_message": task.error_message,
    }
