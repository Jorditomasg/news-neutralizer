"""Search endpoints: topic search and cross-reference."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import SearchTask
from app.schemas import CrossReferenceRequest, SearchRequest, TaskCreated

router = APIRouter()


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
        session_id="default",  # TODO: extract from session/cookie
        query=request.query,
        status="pending",
    )
    db.add(search_task)
    await db.flush()

    # TODO: Enqueue Celery task
    # from app.tasks.search import search_and_analyze_task
    # search_and_analyze_task.delay(task_id, request.query, request.sources)

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
    await db.flush()

    # TODO: Enqueue Celery cross-reference task
    # from app.tasks.search import cross_reference_task
    # cross_reference_task.delay(task_id, request.article_id, request.topics, request.sources)

    return TaskCreated(task_id=task_id)


@router.get("/{task_id}", response_model=None)
async def get_search_results(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the status and results of a search task."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

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

    return task
