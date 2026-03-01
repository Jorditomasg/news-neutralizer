"""Google News RSS search service."""

import urllib.parse
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx
import structlog

from app.services.scraper.search import SearchHit

logger = structlog.get_logger()


def _get_gnews_params(language: str) -> str:
    lang = language.lower()[:2]
    if lang == "en":
        return "hl=en-US&gl=US&ceid=US:en"
    elif lang == "fr":
        return "hl=fr&gl=FR&ceid=FR:fr"
    elif lang == "de":
        return "hl=de&gl=DE&ceid=DE:de"
    elif lang == "it":
        return "hl=it&gl=IT&ceid=IT:it"
    elif lang == "pt":
        return "hl=pt-BR&gl=BR&ceid=BR:pt-419"
    # Default to Spanish
    return "hl=es-ES&gl=ES&ceid=ES:es"

async def search_google_news_rss(query: str, max_results: int = 15, language: str = "es") -> list[SearchHit]:
    """
    Search for articles using Google News RSS.
    
    Args:
        query: The search query.
        max_results: Maximum number of results to return.
        language: ISO 639-1 language code (e.g. 'es', 'en').
        
    Returns:
        List of SearchHit objects.
    """
    # Encode query
    encoded_query = urllib.parse.quote(query)
    
    # Get locale params
    loc_params = _get_gnews_params(language)
    
    # Google News RSS URL
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&{loc_params}"
    
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
                
                # Published date parsing was removed since SearchHit doesn't store it
                
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
