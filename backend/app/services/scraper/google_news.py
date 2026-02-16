"""Google News RSS search service."""

import urllib.parse
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx
import structlog

from app.services.scraper.search import SearchHit

logger = structlog.get_logger()


async def search_google_news_rss(query: str, max_results: int = 15) -> list[SearchHit]:
    """
    Search for articles using Google News RSS.
    
    Args:
        query: The search query.
        max_results: Maximum number of results to return.
        
    Returns:
        List of SearchHit objects.
    """
    # Encode query
    encoded_query = urllib.parse.quote(query)
    
    # Google News RSS URL for Spain (es-ES)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=es-ES&gl=ES&ceid=ES:es"
    
    hits: list[SearchHit] = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(rss_url)
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            
            for entry in feed.entries[:max_results]:
                title = entry.title
                link = entry.link
                source_title = entry.source.title if hasattr(entry, "source") else "Google News"
                
                # Clean title (Google News often formats as "Title - Source")
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    if parts[1] == source_title:
                        title = parts[0]
                
                # Parse date if available
                published_at = None
                if hasattr(entry, "published"):
                    try:
                        published_at = parsedate_to_datetime(entry.published)
                    except Exception:
                        pass
                
                hits.append(SearchHit(
                    url=link,
                    title=title,
                    source_slug="google-news", # Generic slug for aggregated results
                    source_name=source_title,
                ))
                
    except Exception as e:
        logger.error("Google News RSS search failed", query=query, error=str(e))
        return []
        
    logger.info("Google News search complete", query=query, hits=len(hits))
    return hits
