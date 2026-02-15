"""Celery tasks for the search and analysis pipeline.

Uses SYNCHRONOUS SQLAlchemy (psycopg2) instead of async to avoid
asyncpg connection conflicts in forked Celery worker processes.
"""

import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery_app
from app.config import settings
from app.core.security import decrypt_api_key
from app.models import AnalysisResult, Article, SearchTask
from app.services.ai.factory import AIProviderFactory

logger = structlog.get_logger()

# ── Synchronous engine for Celery workers ─────────────────────
# Celery forks worker processes — asyncpg connections can NOT be shared
# across forks. We use psycopg2 (sync) for all DB access in tasks.
_sync_engine = create_engine(
    settings.sync_database_url,
    echo=settings.app_debug,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
SyncSessionLocal = sessionmaker(bind=_sync_engine)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _update_task_progress(task_id: str, status: str, progress: int, error_message: str | None = None):
    """Update task status and progress in the database (sync)."""
    with SyncSessionLocal() as session:
        stmt = (
            update(SearchTask)
            .where(SearchTask.task_id == task_id)
            .values(
                status=status,
                progress=progress,
                error_message=error_message,
                completed_at=datetime.now(timezone.utc) if status in ("completed", "failed") else None,
            )
        )
        session.execute(stmt)
        session.commit()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def search_and_analyze(self, task_id: str, query: str, source_slugs: list | None = None,
                       provider_name: str = "openai", encrypted_api_key: str | None = None):
    """
    Full pipeline: search → scrape → analyze → save.

    This is the main Celery task that orchestrates the entire analysis.
    """
    try:
        _search_and_analyze_sync(
            task_id, query, source_slugs, provider_name, encrypted_api_key
        )
    except Exception as exc:
        logger.error("Task failed", task_id=task_id, error=str(exc))
        try:
            _update_task_progress(task_id, "failed", 0, str(exc))
        except Exception:
            logger.error("Could not update task status after failure", task_id=task_id)
        raise self.retry(exc=exc)


def _search_and_analyze_sync(
    task_id: str, query: str, source_slugs: list | None,
    provider_name: str, encrypted_api_key: str | None
):
    """Synchronous implementation of the full pipeline."""
    from app.services.scraper.search import search_rss_feeds, extract_articles_from_hits

    # ── Step 1: Search RSS feeds ──────────────────────────────
    _update_task_progress(task_id, "scraping", 10)
    logger.info("Step 1: Searching RSS feeds", task_id=task_id, query=query)

    # search_rss_feeds is async, so run it in a temporary event loop
    hits = _run_async(search_rss_feeds(query, source_slugs, max_per_source=3))

    if not hits:
        _update_task_progress(task_id, "failed", 10, "No se encontraron artículos relevantes")
        return

    # ── Step 2: Extract article content ───────────────────────
    _update_task_progress(task_id, "scraping", 30)
    logger.info("Step 2: Extracting articles", task_id=task_id, hits=len(hits))

    extracted = _run_async(extract_articles_from_hits(hits, max_articles=8))

    if not extracted:
        _update_task_progress(task_id, "failed", 30, "No se pudo extraer contenido de los artículos")
        return

    # ── Step 3: Save articles to DB (sync) ────────────────────
    _update_task_progress(task_id, "scraping", 50)

    with SyncSessionLocal() as session:
        stmt = select(SearchTask).where(SearchTask.task_id == task_id)
        result = session.execute(stmt)
        search_task = result.scalar_one()

        db_articles = []
        for article in extracted:
            db_article = Article(
                search_task_id=search_task.id,
                source_name=article.source_name,
                source_url=article.source_url,
                title=article.title,
                body=article.body,
                author=article.author[:200] if article.author else None,
                published_at=article.published_at,
            )
            session.add(db_article)
            db_articles.append(db_article)

        session.commit()

    logger.info("Step 3: Articles saved", task_id=task_id, count=len(db_articles))

    # ── Step 4: AI Analysis ───────────────────────────────────
    _update_task_progress(task_id, "analyzing", 60)
    logger.info("Step 4: Running AI analysis", task_id=task_id, provider=provider_name)

    # Decrypt API key if provided
    api_key = None
    if encrypted_api_key:
        api_key = decrypt_api_key(encrypted_api_key)

    # Prepare article data for the AI
    articles_for_ai = [
        {
            "source_name": a.source_name,
            "title": a.title,
            "body": a.body[:4000],  # Limit body length for token budgets
        }
        for a in extracted
    ]

    try:
        _update_task_progress(task_id, "analyzing", 60)
        logger.info("Step 4: Initializing AI provider", task_id=task_id, provider=provider_name)

        provider = AIProviderFactory.get(provider_name, api_key=api_key)

        _update_task_progress(task_id, "analyzing", 65)
        # AI provider methods are async — Ollama auto-pulls model on first use
        analysis = _run_async(provider.analyze_articles(articles_for_ai))
    except Exception as e:
        error_msg = f"Error en análisis AI ({provider_name}): {str(e)[:500]}"
        logger.error("AI analysis failed", task_id=task_id, error=str(e))
        _update_task_progress(task_id, "failed", 60, error_msg)
        return

    _update_task_progress(task_id, "analyzing", 85)

    # ── Step 5: Save analysis & update article bias scores ────
    with SyncSessionLocal() as session:
        stmt = select(SearchTask).where(SearchTask.task_id == task_id)
        result = session.execute(stmt)
        search_task = result.scalar_one()

        # Save analysis result
        analysis_result = AnalysisResult(
            search_task_id=search_task.id,
            topic_summary=analysis.topic_summary,
            objective_facts=analysis.objective_facts,
            bias_elements=analysis.bias_elements,
            neutralized_summary=analysis.neutralized_summary,
            source_bias_scores=analysis.source_bias_scores,
            provider_used=provider_name,
            tokens_used=analysis.tokens_used,
        )
        session.add(analysis_result)

        # Update article bias scores from analysis
        for source_name, scores in analysis.source_bias_scores.items():
            stmt = (
                update(Article)
                .where(
                    Article.search_task_id == search_task.id,
                    Article.source_name == source_name,
                )
                .values(
                    bias_score=scores.get("score") if isinstance(scores, dict) else None,
                    bias_details=scores if isinstance(scores, dict) else None,
                )
            )
            session.execute(stmt)

        session.commit()

    _update_task_progress(task_id, "completed", 100)
    logger.info("Pipeline complete", task_id=task_id)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def cross_reference_analyze(self, task_id: str, article_id: int, topics: list,
                             source_slugs: list | None = None,
                             provider_name: str = "openai", encrypted_api_key: str | None = None):
    """Cross-reference: search for related articles and run comparative analysis."""
    try:
        query = " ".join(topics)
        _search_and_analyze_sync(
            task_id, query, source_slugs, provider_name, encrypted_api_key
        )
    except Exception as exc:
        logger.error("Cross-reference task failed", task_id=task_id, error=str(exc))
        try:
            _update_task_progress(task_id, "failed", 0, str(exc))
        except Exception:
            logger.error("Could not update task status after failure", task_id=task_id)
        raise self.retry(exc=exc)
