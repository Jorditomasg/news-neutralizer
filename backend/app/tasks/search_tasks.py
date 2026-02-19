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


def _get_ai_provider(provider_name: str, encrypted_api_key: str | None):
    """Create an AI provider, decrypting the key if needed."""
    api_key = None
    if encrypted_api_key:
        api_key = decrypt_api_key(encrypted_api_key)
    return AIProviderFactory.get(provider_name, api_key=api_key)


def _save_analysis(task_id: str, analysis, provider_name: str, extracted_articles):
    """Save analysis result and update article bias scores."""
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


# ══════════════════════════════════════════════════════════════
# Task 1: Topic-based search (existing flow)
# ══════════════════════════════════════════════════════════════

@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def search_and_analyze(self, task_id: str, query: str, source_slugs: list | None = None,
                       provider_name: str = "openai", encrypted_api_key: str | None = None):
    """
    Full pipeline: search → scrape → analyze → save.
    This is the main Celery task for topic-based search.
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
    """Synchronous implementation of the topic-based pipeline."""
    from app.services.scraper.search import search_rss_feeds, extract_articles_from_hits

    # ── Step 1: Search RSS feeds ──────────────────────────────
    # ── Step 1: Search RSS feeds ──────────────────────────────
    _update_task_progress(task_id, "scraping", 5, "Buscando noticias en Google News y RSS...")
    logger.info("Step 1: Searching RSS feeds", task_id=task_id, query=query)

    hits = _run_async(search_rss_feeds(query, source_slugs, max_per_source=3))

    if not hits:
        _update_task_progress(task_id, "failed", 10, "No se encontraron artículos relevantes")
        return

    # ── Step 2: Extract article content ───────────────────────
    logger.info("Step 2: Extracting articles", task_id=task_id, hits=len(hits))
    
    # We use a local extractor to control the loop and report progress
    from app.services.scraper.extractor import ArticleExtractor
    extractor = ArticleExtractor()
    
    extracted = []
    max_articles = 8
    hits_to_process = hits[:max_articles]
    total_hits = len(hits_to_process)
    
    for i, hit in enumerate(hits_to_process):
        try:
            progress_pct = 20 + int((i / total_hits) * 30) # 20% to 50%
            _update_task_progress(task_id, "scraping", progress_pct, f"Extrayendo noticia {i+1} de {total_hits}: {hit.source_name}...")
            
            # extract individual article
            article = _run_async(extractor.extract(hit.url))
            article.source_name = hit.source_name # Ensure source name is preserved
            extracted.append(article)
            
        except Exception as e:
            logger.warning("Article extraction failed", url=hit.url, error=str(e))
            continue

    if not extracted:
        _update_task_progress(task_id, "failed", 50, "No se pudo extraer contenido de los artículos")
        return

    # ── Step 3: Save articles to DB (sync) ────────────────────
    logger.info("Step 3: Saving articles", task_id=task_id, count=len(extracted))

    with SyncSessionLocal() as session:
        stmt = select(SearchTask).where(SearchTask.task_id == task_id)
        result = session.execute(stmt)
        search_task = result.scalar_one()

        for i, article in enumerate(extracted):
            # 50% to 60%
            progress_pct = 50 + int((i / len(extracted)) * 10)
            _update_task_progress(task_id, "scraping", progress_pct, f"Guardando datos: {article.title[:20]}...")
            
            db_article = Article(
                search_task_id=search_task.id,
                source_name=article.source_name,
                source_url=article.source_url,
                title=article.title,
                body=article.body,
                author=article.author[:200] if article.author else None,
                published_at=article.published_at,
                is_source=False,
            )
            session.add(db_article)

        session.commit()

    # ── Step 4: AI Analysis ───────────────────────────────────
    # ── Step 4: AI Analysis ───────────────────────────────────
    _update_task_progress(task_id, "analyzing", 60, "Iniciando análisis de IA. Esto puede tardar unos segundos...")
    logger.info("Step 4: Running AI analysis", task_id=task_id, provider=provider_name)

    articles_for_ai = [
        {
            "source_name": a.source_name,
            "title": a.title,
            "body": a.body[:4000],
        }
        for a in extracted
    ]

    try:
        _update_task_progress(task_id, "analyzing", 65)
        provider = _get_ai_provider(provider_name, encrypted_api_key)
        analysis = _run_async(provider.analyze_articles(articles_for_ai))
    except Exception as e:
        error_msg = f"Error en análisis AI ({provider_name}): {str(e)[:500]}"
        logger.error("AI analysis failed", task_id=task_id, error=str(e))
        _update_task_progress(task_id, "failed", 60, error_msg)
        return

    _update_task_progress(task_id, "analyzing", 85)

    # ── Step 5: Save analysis ─────────────────────────────────
    _save_analysis(task_id, analysis, provider_name, extracted)

    _update_task_progress(task_id, "completed", 100)
    logger.info("Pipeline complete", task_id=task_id)


# ══════════════════════════════════════════════════════════════
# Task 2: URL-based search (new unified flow)
# ══════════════════════════════════════════════════════════════

@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def search_and_analyze_url(self, task_id: str, url: str, source_slugs: list | None = None,
                           provider_name: str = "openai", encrypted_api_key: str | None = None):
    """
    URL pipeline: extract source article → semantic query → search related → analyze.
    Falls back to solo-article analysis if no related articles are found.
    """
    try:
        _search_and_analyze_url_sync(
            task_id, url, source_slugs, provider_name, encrypted_api_key
        )
    except Exception as exc:
        logger.error("URL task failed", task_id=task_id, error=str(exc))
        try:
            _update_task_progress(task_id, "failed", 0, str(exc))
        except Exception:
            logger.error("Could not update task status after failure", task_id=task_id)
        raise self.retry(exc=exc)


def _search_and_analyze_url_sync(
    task_id: str, url: str, source_slugs: list | None,
    provider_name: str, encrypted_api_key: str | None
):
    """Synchronous implementation of the URL-based pipeline."""
    from app.services.scraper.extractor import ArticleExtractor
    from app.services.scraper.search import search_rss_feeds, extract_articles_from_hits

    extractor = ArticleExtractor()

    # ── Step 1: Extract source article from URL ───────────────
    _update_task_progress(task_id, "scraping", 5)
    logger.info("URL Step 1: Extracting source article", task_id=task_id, url=url)

    try:
        source_article = _run_async(extractor.extract(url))
    except Exception as e:
        error_msg = f"No se pudo extraer el artículo de la URL: {str(e)[:300]}"
        logger.error("Source article extraction failed", task_id=task_id, error=str(e))
        _update_task_progress(task_id, "failed", 5, error_msg)
        return

    logger.info("Source article extracted",
                task_id=task_id,
                title=source_article.title[:80],
                source=source_article.source_name)

    # ── Step 2: Save source article to DB ─────────────────────
    _update_task_progress(task_id, "scraping", 15)

    with SyncSessionLocal() as session:
        stmt = select(SearchTask).where(SearchTask.task_id == task_id)
        result = session.execute(stmt)
        search_task = result.scalar_one()

        db_source = Article(
            search_task_id=search_task.id,
            source_name=source_article.source_name,
            source_url=source_article.source_url,
            title=source_article.title,
            body=source_article.body,
            author=source_article.author[:200] if source_article.author else None,
            published_at=source_article.published_at,
            is_source=True,
        )
        session.add(db_source)
        session.commit()

    # ── Step 3: Generate semantic search query via AI ─────────
    _update_task_progress(task_id, "scraping", 25)
    logger.info("URL Step 3: Generating semantic search query", task_id=task_id)

    provider = _get_ai_provider(provider_name, encrypted_api_key)

    try:
        semantic_query = _run_async(
            provider.generate_search_query(source_article.title, source_article.body)
        )
        if not semantic_query or not semantic_query.strip():
            raise ValueError("AI generated an empty semantic query")
    except Exception as e:
        logger.warning("Semantic query generation failed, using title as fallback",
                       task_id=task_id, error=str(e))
        # Fallback: use the first 8 words of the title
        semantic_query = " ".join(source_article.title.split()[:8])

    logger.info("Semantic query generated", task_id=task_id, query=semantic_query)

    # ── Step 4: Search RSS for related articles ───────────────
    _update_task_progress(task_id, "scraping", 35)
    logger.info("URL Step 4: Searching related articles", task_id=task_id, query=semantic_query)

    hits = _run_async(search_rss_feeds(semantic_query, source_slugs, max_per_source=3))

    # Filter out the source URL itself from hits
    hits = [h for h in hits if h.url != url]

    extracted_related = []
    if hits:
        _update_task_progress(task_id, "scraping", 45)
        extracted_related = _run_async(extract_articles_from_hits(hits, max_articles=6))
        logger.info("Related articles extracted", task_id=task_id, count=len(extracted_related))

    # ── Step 5: Save related articles to DB ───────────────────
    if extracted_related:
        _update_task_progress(task_id, "scraping", 55)
        with SyncSessionLocal() as session:
            stmt = select(SearchTask).where(SearchTask.task_id == task_id)
            result = session.execute(stmt)
            search_task = result.scalar_one()

            for article in extracted_related:
                db_article = Article(
                    search_task_id=search_task.id,
                    source_name=article.source_name,
                    source_url=article.source_url,
                    title=article.title,
                    body=article.body,
                    author=article.author[:200] if article.author else None,
                    published_at=article.published_at,
                    is_source=False,
                )
                session.add(db_article)

            session.commit()

        logger.info("Related articles saved", task_id=task_id, count=len(extracted_related))
    else:
        logger.info("No related articles found, will analyze source alone", task_id=task_id)

    # ── Step 6: AI Analysis ───────────────────────────────────
    _update_task_progress(task_id, "analyzing", 65)

    # Build article list: source article first, then related
    articles_for_ai = [
        {
            "role": "MAIN_SOURCE_TO_ANALYZE",
            "source_name": source_article.source_name,
            "title": source_article.title,
            "body": source_article.body[:4000],
        }
    ]
    for a in extracted_related:
        articles_for_ai.append({
            "role": "RELATED_CONTEXT",
            "source_name": a.source_name,
            "title": a.title,
            "body": a.body[:4000],
        })

    try:
        _update_task_progress(task_id, "analyzing", 70)
        analysis = _run_async(provider.analyze_articles(articles_for_ai))
    except Exception as e:
        error_msg = f"Error en análisis AI ({provider_name}): {str(e)[:500]}"
        logger.error("AI analysis failed", task_id=task_id, error=str(e))
        _update_task_progress(task_id, "failed", 70, error_msg)
        return

    _update_task_progress(task_id, "analyzing", 90)

    # ── Step 7: Save analysis ─────────────────────────────────
    all_articles = [source_article] + list(extracted_related)
    _save_analysis(task_id, analysis, provider_name, all_articles)

    _update_task_progress(task_id, "completed", 100)
    logger.info("URL pipeline complete",
                task_id=task_id,
                source_title=source_article.title[:80],
                related_count=len(extracted_related))
