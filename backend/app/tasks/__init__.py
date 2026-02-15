"""Celery task definitions — stubs for now, will be implemented in MVP phase."""

from app.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def search_and_analyze_task(self, task_id: str, query: str, sources: list | None = None):
    """
    Full search flow: scrape → cluster → analyze → save results.

    Steps:
    1. Search across RSS feeds and web scraping for matching articles
    2. Extract article content
    3. Generate embeddings and cluster by topic
    4. Send to LLM for bias analysis
    5. Save results to database
    6. Notify frontend via WebSocket
    """
    # TODO: Implement in MVP phase
    pass


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def cross_reference_task(self, task_id: str, article_id: int, topics: list, sources: list | None = None):
    """
    Cross-reference flow: given one article, find related articles from other sources.

    Steps:
    1. Use extracted topics to search across other sources
    2. Extract content from found articles
    3. Cluster together with the original article
    4. Run comparative bias analysis
    5. Save and notify
    """
    # TODO: Implement in MVP phase
    pass
