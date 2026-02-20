"""History endpoints: paginated list of previous searches and detailed views."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import SearchTask, Article, AnalysisResult
from app.schemas import PaginatedHistoryOut, SearchTaskSummaryOut

router = APIRouter()

@router.get("/", response_model=PaginatedHistoryOut)
async def get_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    query: str | None = Query(None, description="Filter by search query or URL"),
    title: str | None = Query(None, description="Filter by article title"),
    domain: str | None = Query(None, description="Filter by article domain source"),
    db: AsyncSession = Depends(get_db),
):
    """Get a paginated list of historical search tasks."""
    
    # Base query for tasks that are completed
    stmt = select(SearchTask).where(SearchTask.status == "completed")
    count_stmt = select(func.count(SearchTask.id)).where(SearchTask.status == "completed")

    # Joins for filtering
    if title or domain:
        stmt = stmt.outerjoin(SearchTask.articles)
        count_stmt = count_stmt.outerjoin(SearchTask.articles)

    # Apply filters
    if query:
        filter_cond = or_(
            SearchTask.query.ilike(f"%{query}%"),
            SearchTask.source_url.ilike(f"%{query}%")
        )
        stmt = stmt.where(filter_cond)
        count_stmt = count_stmt.where(filter_cond)
        
    if title:
        stmt = stmt.where(Article.title.ilike(f"%{title}%"))
        count_stmt = count_stmt.where(Article.title.ilike(f"%{title}%"))
        
    if domain:
        stmt = stmt.where(Article.source_name.ilike(f"%{domain}%"))
        count_stmt = count_stmt.where(Article.source_name.ilike(f"%{domain}%"))

    # Execute count
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply pagination and sorting
    stmt = stmt.order_by(desc(SearchTask.created_at))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    
    # Pre-load analysis and articles for summary info
    stmt = stmt.options(
        selectinload(SearchTask.analysis),
        selectinload(SearchTask.articles)
    )

    # Execute fetch
    result = await db.execute(stmt)
    # Use unique() if we joined with articles
    if title or domain:
        tasks = result.unique().scalars().all()
    else:
        tasks = result.scalars().all()

    items = []
    for task in tasks:
        provider = task.analysis.provider_used if task.analysis else None
        
        # Find the source article if it exists
        title = None
        source_name = None
        for a in task.articles:
            if a.is_source:
                title = a.title
                source_name = a.source_name
                break

        items.append(
            SearchTaskSummaryOut(
                task_id=task.task_id,
                status=task.status,
                query=task.query,
                source_url=task.source_url,
                title=title,
                source_name=source_name,
                created_at=task.created_at,
                completed_at=task.completed_at,
                provider_used=provider
            )
        )

    return PaginatedHistoryOut(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )


@router.get("/{task_id}")
async def get_history_detail(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the full details of a historical search task."""
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
        raise HTTPException(status_code=404, detail="Task not found")

    # Match the structure of the search endpoint exactly
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
            "trust_score": getattr(a, 'trust_score', None),
            "similarity_score": getattr(a, 'similarity_score', None),
        }
        for a in task.articles
    ]

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
            "model_used": getattr(task.analysis, 'model_used', None),
            "processing_time_ms": getattr(task.analysis, 'processing_time_ms', None),
            "filtered_articles_count": getattr(task.analysis, 'filtered_articles_count', None),
            "avg_similarity_score": getattr(task.analysis, 'avg_similarity_score', None),
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
