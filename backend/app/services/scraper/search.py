"""Multi-source article search — RSS feeds + web scraping."""

from dataclasses import dataclass

import feedparser
import httpx
import structlog

from app.services.scraper.extractor import ArticleExtractor, ExtractedArticle
from app.services.scraper.sources import AVAILABLE_SOURCES, SOURCE_RSS_FEEDS

logger = structlog.get_logger()

_extractor = ArticleExtractor()


@dataclass
class SearchHit:
    """A URL found during search that may be relevant."""
    url: str
    title: str
    source_slug: str
    source_name: str


async def search_rss_feeds(
    query: str,
    source_slugs: list[str] | None = None,
    max_per_source: int = 5,
) -> list[SearchHit]:
    """
    Search for articles matching a query across RSS feeds.

    Args:
        query: Keywords to search for (case-insensitive substring match).
        source_slugs: Specific sources to search (None = all).
        max_per_source: Max articles to return per source.

    Returns:
        List of SearchHit with URLs and titles.
    """
    query_lower = query.strip().lower()
    
    # Early escape to avoid returning global top news
    if not query_lower:
        logger.warning("Search query is empty, aborting RSS search to prevent top news fallback")
        return []
        
    query_terms = query_lower.split()
    hits: list[SearchHit] = []

    # Determine which sources to search
    slugs_to_search = source_slugs or [s.slug for s in AVAILABLE_SOURCES if s.enabled]

    # If source_slugs is empty/None, use Google News for better relevance on general topics
    if not source_slugs and not slugs_to_search:
        # Import here to avoid circular dependencies if any
        from app.services.scraper.google_news import search_google_news_rss
        return await search_google_news_rss(query, max_results=max_per_source * 3)

    # Otherwise search specific RSS feeds
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for slug in slugs_to_search:
            feed_urls = SOURCE_RSS_FEEDS.get(slug, [])
            source_name = next((s.name for s in AVAILABLE_SOURCES if s.slug == slug), slug)

            for feed_url in feed_urls:
                try:
                    response = await client.get(feed_url, headers={
                        "User-Agent": "NewsNeutralizer/1.0 (RSS Reader)"
                    })
                    response.raise_for_status()

                    feed = feedparser.parse(response.text)
                    count = 0

                    for entry in feed.entries:
                        if count >= max_per_source:
                            break

                        title = getattr(entry, "title", "")
                        summary = getattr(entry, "summary", "")
                        link = getattr(entry, "link", "")

                        # Check if any query term appears in title or summary
                        text = f"{title} {summary}".lower()
                        if any(term in text for term in query_terms) and link:
                            hits.append(SearchHit(
                                url=link,
                                title=title,
                                source_slug=slug,
                                source_name=source_name,
                            ))
                            count += 1

                except Exception as e:
                    logger.warning("RSS feed fetch failed", feed_url=feed_url, error=str(e))
                    continue

    logger.info("RSS search complete", query=query, hits_found=len(hits))
    return hits


async def extract_articles_from_hits(
    hits: list[SearchHit],
    max_articles: int = 10,
) -> list[ExtractedArticle]:
    """
    Extract full article content from search hits.

    Args:
        hits: SearchHit list from RSS search.
        max_articles: Maximum total articles to extract.

    Returns:
        List of successfully extracted articles.
    """
    articles: list[ExtractedArticle] = []

    for hit in hits[:max_articles]:
        try:
            article = await _extractor.extract(hit.url)
            # Override source_name with the known source name
            article.source_name = hit.source_name
            articles.append(article)
            logger.info("Extracted article", source=hit.source_name, title=article.title[:80])
        except Exception as e:
            logger.warning("Article extraction failed", url=hit.url, error=str(e))
            continue

    logger.info("Extraction complete", extracted=len(articles), attempted=min(len(hits), max_articles))
    return articles
