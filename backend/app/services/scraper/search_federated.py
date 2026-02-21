import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import structlog

# We'll use the existing DDGS for DuckDuckGo and httpx for Google News
from duckduckgo_search import DDGS
import feedparser
import httpx

logger = structlog.get_logger(__name__)

@dataclass
class ArticleHit:
    """A search result hit from any provider."""
    url: str
    title: str
    source_name: str
    provider: str  # Which search engine found this (e.g., 'ddg', 'gnews')
    published_date: Optional[str] = None
    snippet: Optional[str] = None


class SearchProvider(ABC):
    """Abstract interface for a news search provider."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[ArticleHit]:
        """Execute the search and return normalized hits."""
        pass


class DuckDuckGoNewsProvider(SearchProvider):
    """Scrapes DuckDuckGo News. Excellent for fresh global results without API keys."""
    
    @property
    def name(self) -> str:
        return "duckduckgo"
        
    async def search(self, query: str, max_results: int = 15) -> List[ArticleHit]:
        logger.info("Searching DDG News", query=query)
        hits = []
        try:
            # DDGS is synchronous by default, so we wrap it in an executor
            def _do_search():
                with DDGS() as ddgs:
                    # 'timelimit' can be 'd' (day), 'w' (week), 'm' (month)
                    results = list(ddgs.news(query, max_results=max_results, timelimit="w"))
                    return results

            results = await asyncio.to_thread(_do_search)
            
            for index, res in enumerate(results):
                hits.append(ArticleHit(
                    url=res.get("url", ""),
                    title=res.get("title", ""),
                    source_name=res.get("source", "Unknown"),
                    published_date=res.get("date", ""),
                    snippet=res.get("body", ""),
                    provider=self.name
                ))
                
        except Exception as e:
            logger.error("DDG Search failed", error=str(e))
            
        return hits


class GoogleNewsRSSProvider(SearchProvider):
    """Fallback Google News RSS searcher."""
    
    @property
    def name(self) -> str:
        return "google_news"
        
    async def search(self, query: str, max_results: int = 15) -> List[ArticleHit]:
        from urllib.parse import quote_plus
        
        logger.info("Searching Google News RSS", query=query)
        encoded_query = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=es&gl=ES&ceid=ES:es"
        
        hits = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                for entry in feed.entries[:max_results]:
                    # Google News concatenates "Title - SourceName". Let's split it if possible.
                    title = getattr(entry, "title", "")
                    source_name = getattr(getattr(entry, "source", None), "title", "Google News")
                    if " - " in title and source_name == "Google News":
                        parts = title.rsplit(" - ", 1)
                        title = parts[0]
                        source_name = parts[1]
                        
                    hits.append(ArticleHit(
                        url=getattr(entry, "link", ""),
                        title=title,
                        source_name=source_name,
                        published_date=getattr(entry, "published", ""),
                        provider=self.name
                    ))
        except Exception as e:
            logger.error("Google News RSS search failed", error=str(e))
            
        return hits


class FederatedSearchEngine:
    """Orchestrates multiple search providers concurrently."""
    
    def __init__(self):
        self.providers: List[SearchProvider] = [
            DuckDuckGoNewsProvider(),
            GoogleNewsRSSProvider()
        ]
        
    async def _resolve_google_news_urls(self, hits: List[ArticleHit]) -> List[ArticleHit]:
        """
        Batch-resolve Google News redirect URLs to their canonical destinations.
        This must happen BEFORE deduplication so we can detect that a Google News
        URL and a direct URL point to the same article.
        """
        from app.services.scraper.url_utils import is_google_news_url
        from app.services.scraper.resolvers.redirect_resolver import RedirectResolver
        
        resolver = RedirectResolver()
        resolved_hits = []
        
        for hit in hits:
            if is_google_news_url(hit.url):
                try:
                    resolved_url = await resolver.resolve(hit.url)
                    logger.info("Resolved Google News URL", 
                               original=hit.url[:80], resolved=resolved_url[:80])
                    hit.url = resolved_url
                except Exception as e:
                    logger.warning("Failed to resolve Google News URL, keeping original",
                                   url=hit.url[:80], error=str(e))
            resolved_hits.append(hit)
            
        return resolved_hits
        
    async def search(self, query: str, max_results_per_provider: int = 20) -> List[ArticleHit]:
        """
        Runs all providers concurrently and merges the results.
        Resolves Google News redirects, then deduplicates by normalized URL.
        """
        from app.services.scraper.url_utils import normalize_url
        
        if not query.strip():
            return []
            
        tasks = [
            provider.search(query, max_results=max_results_per_provider)
            for provider in self.providers
        ]
        
        # Run all searches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all raw hits
        raw_hits = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                provider_name = self.providers[idx].name
                logger.error("Provider failed in federated search", provider=provider_name, error=str(result))
                continue
            raw_hits.extend(result)
        
        # Resolve Google News URLs to canonical destinations
        resolved_hits = await self._resolve_google_news_urls(raw_hits)
        
        # Deduplicate by normalized URL (prefers first occurrence — DDG runs before GNews)
        all_hits = []
        seen_normalized = set()
        
        for hit in resolved_hits:
            norm = normalize_url(hit.url)
            if norm not in seen_normalized:
                seen_normalized.add(norm)
                all_hits.append(hit)
            else:
                logger.info("Duplicate URL removed", url=hit.url[:80], normalized=norm[:80])
                    
        logger.info("Federated search complete", query=query, 
                     total_raw=len(raw_hits), after_dedup=len(all_hits))
        return all_hits
