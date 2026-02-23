"""Celery tasks for the search and analysis pipeline.

Uses SYNCHRONOUS SQLAlchemy (psycopg2) instead of async to avoid
asyncpg connection conflicts in forked Celery worker processes.
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.models import AnalysisResult, Article, SearchTask
from app.tasks._celery_infra import SyncSessionLocal, run_async, get_ai_provider

logger = structlog.get_logger()


def _record_paywall_hit(domain: str, is_truncated: bool, indicators: list[str]):
    """If an article was detected as truncated, mark the domain."""
    if not is_truncated:
        return
    from app.models.domain import SourceDomain
    from app.services.reliability import update_domain_reliability
    with SyncSessionLocal() as session:
        stmt = select(SourceDomain).where(SourceDomain.domain == domain)
        domain_entry = session.execute(stmt).scalar_one_or_none()
        if domain_entry:
            domain_entry.has_paywall = True
            domain_entry.paywall_hits_count = (domain_entry.paywall_hits_count or 0) + 1
            session.commit()
            update_domain_reliability(session, domain)
        else:
            # Domain not yet tracked — create it with paywall flag
            new_dom = SourceDomain(domain=domain, is_evaluated=False, has_paywall=True, paywall_hits_count=1)
            session.add(new_dom)
            session.commit()
        logger.info("Paywall hit recorded", domain=domain, indicators=indicators)


def _update_task_progress(task_id: str, status: str, progress: int, error_message: str | None = None, progress_message: str | None = None):
    """Update task status and progress in the database (sync)."""
    with SyncSessionLocal() as session:
        values_dict = {
            "status": status,
            "progress": progress,
            "completed_at": datetime.now(timezone.utc) if status in ("completed", "failed") else None,
        }
        if error_message is not None:
            values_dict["error_message"] = error_message
        if progress_message is not None:
            values_dict["progress_message"] = progress_message

        stmt = (
            update(SearchTask)
            .where(SearchTask.task_id == task_id)
            .values(**values_dict)
        )
        session.execute(stmt)
        session.commit()


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
        return analysis_result


def _copy_cached_result_to_task(session: Session, new_task_id: str, cached_result: AnalysisResult):
    """Deep-copy a cached analysis and its articles to a new SearchTask."""
    stmt = select(SearchTask).where(SearchTask.task_id == new_task_id)
    new_task = session.execute(stmt).scalar_one()
    
    # Get original articles
    orig_stmt = select(Article).where(Article.search_task_id == cached_result.search_task_id)
    orig_articles = session.execute(orig_stmt).scalars().all()
    
    for a in orig_articles:
        new_article = Article(
            search_task_id=new_task.id,
            source_name=a.source_name,
            source_url=a.source_url,
            title=a.title,
            body=a.body,
            author=a.author,
            published_at=a.published_at,
            is_source=a.is_source,
            bias_score=a.bias_score,
            bias_details=a.bias_details,
            cluster_id=a.cluster_id,
            trust_score=a.trust_score,
            similarity_score=a.similarity_score,
            is_truncated=a.is_truncated,
        )
        session.add(new_article)
        
    analysis_copy = AnalysisResult(
        search_task_id=new_task.id,
        topic_summary=cached_result.topic_summary,
        objective_facts=cached_result.objective_facts,
        bias_elements=cached_result.bias_elements,
        neutralized_summary=cached_result.neutralized_summary,
        source_bias_scores=cached_result.source_bias_scores,
        provider_used=cached_result.provider_used,
        model_used=cached_result.model_used,
        processing_time_ms=0,
        filtered_articles_count=cached_result.filtered_articles_count,
        avg_similarity_score=cached_result.avg_similarity_score,
        tokens_used=0,
    )
    session.add(analysis_copy)
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
    import hashlib
    from app.services.scraper.extractor import ArticleExtractor
    from app.services.scraper.search_federated import FederatedSearchEngine
    from app.services.ai.clustering import SemanticClusterer
    from app.services.scraper.domain_filter import DomainFilter
    from app.services.cache_manager import SyncCacheManager
    from app.services.scraper.extractor import ExtractedArticle
    from app.models.domain import TopicCache
    from urllib.parse import urlparse

    # ── Check Query Cache first ───────────────────────────────
    with SyncSessionLocal() as session:
        cache_manager = SyncCacheManager(session)
        cached_result = cache_manager.get_cached_query(query)
        if cached_result:
            logger.info("Using cached query result", task_id=task_id, query=query)
            _copy_cached_result_to_task(session, task_id, cached_result)
            _update_task_progress(task_id, "completed", 100)
            return

    # ── Topic Specificity Check (LLM, with DB cache) ──────────
    _update_task_progress(task_id, "scraping", 2, progress_message="Validando especificidad del tema...")
    normalized_topic = query.strip().lower()
    topic_hash = hashlib.sha256(normalized_topic.encode()).hexdigest()

    # Check if we already have a cached result for this topic
    topic_is_cached = False
    with SyncSessionLocal() as session:
        from sqlalchemy import select as sa_select
        stmt = sa_select(TopicCache).where(TopicCache.topic_hash == topic_hash)
        cached_topic = session.execute(stmt).scalar_one_or_none()
        if cached_topic:
            topic_is_cached = True
            if not cached_topic.is_specific:
                _update_task_progress(task_id, "failed", 5, cached_topic.reason)
                return

    if not topic_is_cached:
        try:
            provider = get_ai_provider(provider_name, encrypted_api_key)
            ai_result = run_async(provider.evaluate_topic_specificity(query))

            # Cache the result
            with SyncSessionLocal() as session:
                new_cache = TopicCache(
                    topic_hash=topic_hash,
                    topic_text=normalized_topic,
                    is_specific=ai_result.get("is_specific", True),
                    reason=ai_result.get("reason", "")
                )
                session.add(new_cache)
                session.commit()

            if not ai_result.get("is_specific", True):
                reason = ai_result.get("reason", "Tema demasiado genérico o ambiguo.")
                _update_task_progress(task_id, "failed", 5, f"AMBIGUOUS_TOPIC: {reason}")
                return
        except Exception as e:
            logger.warning("Topic specificity check failed, proceeding with search", error=str(e))
            # Fail open: allow the search if LLM check fails

    extractor = ArticleExtractor()
    federator = FederatedSearchEngine()
    clusterer = SemanticClusterer(similarity_threshold=0.85)
    domain_filter = DomainFilter(min_trust_score=40)

    # ── Step 1: Search RSS feeds ──────────────────────────────
    _update_task_progress(task_id, "scraping", 5, "Buscando noticias en modo federado (Global)...")
    logger.info("Step 1: Searching Federated Sources", task_id=task_id, query=query)

    hits = run_async(federator.search(query, max_results_per_provider=20))

    if not hits:
        _update_task_progress(task_id, "failed", 10, "No se encontraron artículos relevantes en ninguna fuente")
        return
        
    # Domain Trust Filtering
    # Remove articles from known low-trust domains before clustering
    hits = domain_filter.filter_untrusted_hits(hits)
    
    if not hits:
        _update_task_progress(task_id, "failed", 10, "Los resultados provenían de fuentes de baja confianza")
        return

    # Semantic Clustering Phase for manual queries
    _update_task_progress(task_id, "scraping", 15, "Agrupando noticias por similitud semántica...")
    logger.info("Semantic filtering of manual query", found=len(hits))

    # We use DBSCAN to find the densest chunk of related news
    filtered_hits = clusterer.get_densest_cluster(hits)
    
    # Take top 8
    hits_to_process = filtered_hits[:8]

    if not hits_to_process:
        _update_task_progress(task_id, "failed", 10, "No se pudieron agrupar semánticamente los artículos")
        return

    # We already have an extractor initialized at the top
    
    extracted = []
    total_hits = len(hits_to_process)
    
    for i, hit in enumerate(hits_to_process):
        try:
            progress_pct = 20 + int((i / total_hits) * 30) # 20% to 50%
            _update_task_progress(task_id, "scraping", progress_pct, f"Extrayendo noticia {i+1} de {total_hits}: {hit.source_name}...")
            
            with SyncSessionLocal() as session:
                cache_manager = SyncCacheManager(session)
                cached = cache_manager.get_cached_article(hit.url)
                if cached:
                    logger.info("Using cached article", url=hit.url)
                    article = ExtractedArticle(
                        title=cached.title,
                        body=cached.body,
                        source_name=hit.source_name,
                        source_url=hit.url,
                        published_at=cached.published_at
                    )
                else:
                    # extract individual article
                    article = run_async(extractor.extract(hit.url))
                    article.source_name = hit.source_name # Ensure source name is preserved
                    
                    domain = urlparse(article.source_url).netloc
                    cache_manager.set_cached_article(
                        url=hit.url,
                        canonical_url=article.source_url,
                        domain=domain,
                        title=article.title,
                        body=article.body,
                        published_at=article.published_at
                    )
                    # Record paywall hit if detected
                    if article.is_truncated:
                        _record_paywall_hit(domain, True, article.paywall_indicators)
                    
            extracted.append(article)
            
        except Exception as e:
            logger.warning("Article extraction failed", url=hit.url, error=str(e))
            continue

    if not extracted:
        _update_task_progress(task_id, "failed", 50, "No se pudo extraer contenido de los artículos")
        return

    # ── Post-extraction dedup by canonical URL ────────────────
    from app.services.scraper.url_utils import normalize_url
    seen_canonical = set()
    deduped = []
    for article in extracted:
        canonical = normalize_url(article.source_url)
        if canonical not in seen_canonical:
            seen_canonical.add(canonical)
            deduped.append(article)
        else:
            logger.info("Post-extraction duplicate removed", url=article.source_url[:80])
    extracted = deduped

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
                is_truncated=getattr(article, 'is_truncated', False),
            )
            session.add(db_article)

        session.commit()

    # Trigger domain evaluation in the background (fire and forget)
    urls_to_evaluate = [a.source_url for a in extracted]
    if urls_to_evaluate:
        from app.tasks.domain_tasks import discover_and_evaluate_domains
        discover_and_evaluate_domains.delay(urls_to_evaluate, provider_name, encrypted_api_key)

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
        provider = get_ai_provider(provider_name, encrypted_api_key)
        analysis = run_async(provider.analyze_articles(articles_for_ai))
    except Exception as e:
        error_msg = f"Error en análisis AI ({provider_name}): {str(e)[:500]}"
        logger.error("AI analysis failed", task_id=task_id, error=str(e))
        _update_task_progress(task_id, "failed", 60, error_msg)
        return

    _update_task_progress(task_id, "analyzing", 85)

    # ── Step 5: Save analysis ─────────────────────────────────
    analysis_result = _save_analysis(task_id, analysis, provider_name, extracted)
    
    with SyncSessionLocal() as session:
        cache_manager = SyncCacheManager(session)
        cache_manager.set_cached_query(query, analysis_result.id)

    _update_task_progress(task_id, "completed", 100)
    logger.info("Pipeline complete", task_id=task_id)


# ══════════════════════════════════════════════════════════════
# Task 2: URL-based search (new unified flow)
# ══════════════════════════════════════════════════════════════

@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def search_and_analyze_url(self, task_id: str, url: str, original_query: str | None = None, source_slugs: list | None = None,
                           provider_name: str = "openai", encrypted_api_key: str | None = None):
    """
    URL pipeline: extract source article → semantic query → search related → analyze.
    Falls back to solo-article analysis if no related articles are found.
    """
    try:
        _search_and_analyze_url_sync(
            task_id, url, original_query, source_slugs, provider_name, encrypted_api_key
        )
    except Exception as exc:
        logger.error("URL task failed", task_id=task_id, error=str(exc))
        try:
            _update_task_progress(task_id, "failed", 0, str(exc))
        except Exception:
            logger.error("Could not update task status after failure", task_id=task_id)
        raise self.retry(exc=exc)


def _search_and_analyze_url_sync(
    task_id: str, url: str, original_query: str | None, source_slugs: list | None,
    provider_name: str, encrypted_api_key: str | None
):
    """Synchronous implementation of the URL-based pipeline (Fact-Based Analysis)."""
    from app.services.scraper.extractor import ArticleExtractor
    from app.services.scraper.search_federated import FederatedSearchEngine
    from app.services.cache_manager import SyncCacheManager
    from app.services.scraper.extractor import ExtractedArticle
    from app.models.domain import Article, ArticleStatus, StructuredFact, AnalysisResult
    from app.core.chunking import segment_text_into_chunks
    from app.services.scraper.url_utils import normalize_url
    from urllib.parse import urlparse

    extractor = ArticleExtractor()
    federator = FederatedSearchEngine()
    provider = get_ai_provider(provider_name, encrypted_api_key)

    # ── Step 1: Extract source article from URL ───────────────
    _update_task_progress(task_id, "scraping", 0, progress_message="Descargando contenido del artículo...")
    logger.info("URL Step 1: Extracting source article", task_id=task_id, url=url)

    try:
        with SyncSessionLocal() as session:
            # Fast-track check conceptually happens before/during Extraction phase
            # For now, we still extract to ensure we have content if not cached
            cache_manager = SyncCacheManager(session)
            cached = cache_manager.get_cached_article(url)
            if cached:
                logger.info("Using cached source article", url=url)
                source_article = ExtractedArticle(
                    title=cached.title,
                    body=cached.body,
                    source_name=cached.domain,
                    source_url=url,
                    published_at=cached.published_at
                )
            else:
                source_article = run_async(extractor.extract(url))
                domain = urlparse(source_article.source_url).netloc
                cache_manager.set_cached_article(
                    url=url,
                    canonical_url=source_article.source_url,
                    domain=domain,
                    title=source_article.title,
                    body=source_article.body,
                    published_at=source_article.published_at
                )
    except Exception as e:
        error_msg = f"No se pudo extraer el artículo de la URL: {str(e)[:300]}"
        logger.error("Source article extraction failed", task_id=task_id, error=str(e))
        _update_task_progress(task_id, "failed", 5, error_msg)
        return

    # Record paywall hit on the domain if detected
    from urllib.parse import urlparse as _urlparse
    source_domain = _urlparse(source_article.source_url).netloc
    if source_domain.startswith("www."):
        source_domain = source_domain[4:]
    if source_article.is_truncated:
        _record_paywall_hit(source_domain, True, source_article.paywall_indicators)

    # ── Step 1.5: Find related articles to provide context ────
    _update_task_progress(task_id, "scraping", 5, progress_message="Buscando noticias relacionadas para comparar...")
    related_hits = []
    try:
        # Use simple federated search on the title
        related_hits = run_async(federator.search(source_article.title, max_results_per_provider=5))
    except Exception as e:
        logger.warning("Failed to fetch related articles during URL analysis", error=str(e))
        
    # We will just save them as detected articles so they appear in the UI
    related_articles_data = []
    for hit in related_hits[:8]: # Limit to 8
        if normalize_url(hit.url) != normalize_url(source_article.source_url):
            related_articles_data.append(hit)

    # ── Step 2: Chunking ──────────────────────────────────────
    _update_task_progress(task_id, "analyzing", 10, progress_message="Segmentando artículo en bloques semánticos...")
    chunks = segment_text_into_chunks(source_article.body, max_tokens=1500)
    total_chunks = len(chunks)

    # ── Step 3: Save initial Article to database ─────────────
    with SyncSessionLocal() as session:
        stmt = select(SearchTask).where(SearchTask.task_id == task_id)
        search_task = session.execute(stmt).scalar_one()

        # Update SearchTask with the resolved (canonical) URL and article title
        search_task.source_url = source_article.source_url
        search_task.query = source_article.title

        db_article = Article(
            search_task_id=search_task.id,
            source_name=source_article.source_name,
            source_url=source_article.source_url,
            title=source_article.title,
            body=source_article.body,
            author=source_article.author[:200] if source_article.author else None,
            published_at=source_article.published_at,
            is_source=True,
            is_truncated=source_article.is_truncated,
            status=ArticleStatus.ANALYZING
        )
        session.add(db_article)
        session.flush()
        article_id = db_article.id
        
        # Save related articles
        for hit in related_articles_data:
            rel_article = Article(
                search_task_id=search_task.id,
                source_name=hit.source_name,
                source_url=hit.url,
                title=hit.title,
                body="", # We don't fetch body yet
                published_at=hit.published_at,
                is_source=False,
                status=ArticleStatus.DETECTED
            )
            session.add(rel_article)
            
        session.commit()

    # ── Step 4: Process Chunks (parallel for external APIs) ─────
    import asyncio
    
    # Ollama is single-GPU sequential; external APIs can handle concurrency
    is_local_model = provider.name == "ollama"
    max_concurrency = 1 if is_local_model else 3
    
    async def _process_chunks_parallel(chunks_list, ai_provider, concurrency):
        """Process chunks with controlled concurrency."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_one(chunk_text, chunk_idx):
            async with semaphore:
                result = await ai_provider.extract_facts_from_chunk(chunk_text)
                return chunk_idx, result
        
        tasks = [process_one(c, i) for i, c in enumerate(chunks_list, 1)]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    _update_task_progress(task_id, "analyzing", 15, progress_message=f"Extrayendo hechos de {total_chunks} bloques...")
    
    chunk_results = run_async(_process_chunks_parallel(chunks, provider, max_concurrency))
    
    extracted_facts_all = []
    pending_facts = []  # Accumulate StructuredFacts for batch insert
    
    for result in chunk_results:
        if isinstance(result, Exception):
            logger.error("Error extracting chunk", task_id=task_id, error=str(result))
            continue
        
        chunk_idx, chunk_result = result
        
        # Accumulate facts for batch insert
        for fact in chunk_result.facts:
            pending_facts.append(StructuredFact(article_id=article_id, content=fact, type="FACT", chunk_index=chunk_idx))
        for claim in chunk_result.unverified_claims:
            pending_facts.append(StructuredFact(article_id=article_id, content=claim, type="UNVERIFIED_CLAIM", chunk_index=chunk_idx))
        for bias in chunk_result.biases:
            pending_facts.append(StructuredFact(article_id=article_id, content=f"{bias.get('type')}: {bias.get('quote')} - {bias.get('explanation')}", type="BIAS", chunk_index=chunk_idx))
        for frame in chunk_result.framing:
            pending_facts.append(StructuredFact(article_id=article_id, content=frame, type="FRAMING", chunk_index=chunk_idx))
        
        if chunk_result.entities:
            pending_facts.append(StructuredFact(article_id=article_id, content="Entidades detectadas", type="ENTITIES", entities=chunk_result.entities, chunk_index=chunk_idx))
        if chunk_result.tone:
            pending_facts.append(StructuredFact(article_id=article_id, content=chunk_result.tone, type="TONE", chunk_index=chunk_idx))
            
        extracted_facts_all.extend(chunk_result.facts)

    # Batch insert all accumulated facts in a single session
    if pending_facts:
        with SyncSessionLocal() as session:
            session.add_all(pending_facts)
            session.commit()
        logger.info("Batch inserted chunk facts", count=len(pending_facts), task_id=task_id)

    # ── Step 5: Consolidate & Embeddings ───────────────────────
    _update_task_progress(task_id, "analyzing", 90, progress_message="Consolidando hechos atómicos extraídos...")
    
    # Skip LLM consolidation for short articles (single chunk or few facts)
    if len(extracted_facts_all) > 5 and total_chunks > 1:
        try:
            consolidated_facts = run_async(provider.consolidate_intra_article_facts(extracted_facts_all))
        except Exception as e:
            logger.error("Error deduplicating facts", error=str(e))
            consolidated_facts = extracted_facts_all
    else:
        logger.info("Skipping LLM consolidation (single chunk or few facts)", 
                     facts_count=len(extracted_facts_all), chunks=total_chunks, task_id=task_id)
        consolidated_facts = extracted_facts_all
        
    from app.services.ai.clustering import generate_embeddings
    embeddings = generate_embeddings(consolidated_facts)

    # Build AnalysisResult using real extracted data (not hardcoded values)
    with SyncSessionLocal() as session:
        stmt = select(SearchTask).where(SearchTask.task_id == task_id)
        search_task = session.execute(stmt).scalar_one()

        article = session.get(Article, article_id)
        article.status = ArticleStatus.ANALYZED
        article.analyzed_at = datetime.now(timezone.utc)
        
        # Replace raw FACT entries with consolidated + embedded versions
        from sqlalchemy import delete
        session.execute(delete(StructuredFact).where(StructuredFact.article_id == article_id, StructuredFact.type == "FACT"))
        
        for fact, emb in zip(consolidated_facts, embeddings):
            session.add(StructuredFact(
                article_id=article_id,
                content=fact,
                type="FACT",
                chunk_index=0,
                embedding=emb if len(emb) > 0 else None
            ))
        
        # Collect real bias elements from extracted chunks
        bias_facts = session.execute(
            select(StructuredFact).where(
                StructuredFact.article_id == article_id,
                StructuredFact.type.in_(["BIAS", "FRAMING"])
            )
        ).scalars().all()
        
        real_bias_elements = []
        for bf in bias_facts:
            # Parse back "type: quote - explanation" if possible
            content = bf.content
            b_type = bf.type.capitalize()
            quote = ""
            explanation = content
            
            if ": " in content and " - " in content:
                parts = content.split(": ", 1)
                b_type = parts[0]
                remainder = parts[1]
                if " - " in remainder:
                    quote, explanation = remainder.split(" - ", 1)
                else:
                    explanation = remainder
                    
            real_bias_elements.append({
                "source": source_article.source_name,
                "type": b_type,
                "original_text": quote or "Texto no extraído individualmente",
                "explanation": explanation,
                "severity": 3  # Default severity since it's not currently extracted
            })
        
        # Build a real summary from consolidated facts
        summary_text = ". ".join(consolidated_facts[:7]) + "." if consolidated_facts else "No se extrajeron hechos."
        
        # Clear any existing analysis result (in case of retry)
        session.execute(delete(AnalysisResult).where(AnalysisResult.search_task_id == search_task.id))
        
        analysis = AnalysisResult(
            search_task_id=search_task.id,
            topic_summary=f"Análisis estructurado: {source_article.title[:100]}",
            objective_facts=consolidated_facts,
            bias_elements=real_bias_elements,
            neutralized_summary=summary_text,
            source_bias_scores={source_article.source_name: {
                "score": round(len(real_bias_elements) / max(len(consolidated_facts), 1), 2),
                "direction": "por determinar",
                "confidence": round(min(len(consolidated_facts) / 10, 1.0), 2)
            }},
            provider_used=provider_name,
            model_used=provider.name,
            processing_time_ms=0,
            filtered_articles_count=0,
            avg_similarity_score=1.0,
            tokens_used=0
        )
        session.add(analysis)
        search_task.completed_at = datetime.now(timezone.utc)
        search_task.status = "completed"
        search_task.progress = 100
        session.commit()
        logger.info(f"Article analysis completed", task_id=task_id, article_id=article_id,
                     facts=len(consolidated_facts), biases=len(real_bias_elements))
        
    # Phase 6: Trigger check for new context availability on existing generated news
    from app.tasks.generate_tasks import check_new_context_availability
    check_new_context_availability.delay(article_id)
        
    _update_task_progress(task_id, "completed", 100, progress_message="Análisis estructurado completado con éxito.")
    logger.info("URL pipeline complete", task_id=task_id, source_title=source_article.title[:80])
