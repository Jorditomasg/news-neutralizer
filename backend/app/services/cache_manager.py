import hashlib
from datetime import datetime, timedelta, timezone
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import structlog

from app.models.domain import ArticleCache, QueryCache, AnalysisResult

logger = structlog.get_logger(__name__)

class CacheManager:
    """Manages database-backed caching for articles and queries."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.article_ttl_days = 7
        self.query_ttl_hours = 24

    def _hash_string(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
        
    def _normalize_query(self, query: str) -> str:
        return query.strip().lower()

    async def get_cached_article(self, url: str) -> ArticleCache | None:
        """Retrieve an unexpired article from cache by URL."""
        url_hash = self._hash_string(url)
        stmt = select(ArticleCache).where(
            ArticleCache.url_hash == url_hash,
            ArticleCache.expires_at > datetime.now(timezone.utc)
        )
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()
        
        if cached:
            logger.info("Article cache hit", url=url)
        else:
            logger.debug("Article cache miss", url=url)
            
        return cached

    async def set_cached_article(self, url: str, canonical_url: str, domain: str, title: str, body: str, published_at: datetime | None, embedding_vector: list[float] | None = None) -> ArticleCache:
        """Save recently extracted and embedded article into cache."""
        url_hash = self._hash_string(url)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.article_ttl_days)
        
        # Upsert logic (simplest way in SQLAlchemy async is merge or just query and update)
        stmt = select(ArticleCache).where(ArticleCache.url_hash == url_hash)
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()
        
        if cached:
            cached.title = title
            cached.body = body
            cached.published_at = published_at
            cached.embedding_vector = embedding_vector
            cached.expires_at = expires_at
        else:
            cached = ArticleCache(
                url_hash=url_hash,
                url_canonical=canonical_url,
                domain=domain,
                title=title,
                body=body,
                published_at=published_at,
                embedding_vector=embedding_vector,
                expires_at=expires_at
            )
            self.session.add(cached)
            
        await self.session.commit()
        return cached

    async def get_cached_query(self, query: str) -> AnalysisResult | None:
        """Retrieve the analysis result for a given query if valid and unexpired."""
        norm_query = self._normalize_query(query)
        query_hash = self._hash_string(norm_query)
        
        stmt = select(QueryCache).where(
            QueryCache.query_hash == query_hash,
            QueryCache.expires_at > datetime.now(timezone.utc)
        )
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()
        
        if cached and cached.analysis_result_id:
            logger.info("Query cache hit", query=query)
            analysis_stmt = select(AnalysisResult).where(AnalysisResult.id == cached.analysis_result_id)
            analysis_result = await self.session.execute(analysis_stmt)
            return analysis_result.scalar_one_or_none()
            
        logger.debug("Query cache miss", query=query)
        return None

    async def set_cached_query(self, query: str, analysis_result_id: int) -> QueryCache:
        """Save a new query and its analysis result id to the cache."""
        norm_query = self._normalize_query(query)
        query_hash = self._hash_string(norm_query)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.query_ttl_hours)
        
        stmt = select(QueryCache).where(QueryCache.query_hash == query_hash)
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()
        
        if cached:
            cached.analysis_result_id = analysis_result_id
            cached.expires_at = expires_at
        else:
            cached = QueryCache(
                query_hash=query_hash,
                query_text=norm_query,
                analysis_result_id=analysis_result_id,
                expires_at=expires_at
            )
            self.session.add(cached)
            
        await self.session.commit()
        return cached

    async def invalidate_article(self, url: str) -> None:
        """Invalidate a cached article."""
        url_hash = self._hash_string(url)
        stmt = select(ArticleCache).where(ArticleCache.url_hash == url_hash)
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()
        if cached:
            await self.session.delete(cached)
            await self.session.commit()


class SyncCacheManager:
    """Synchronous version for Celery workers."""
    
    def __init__(self, session: Session):
        self.session = session
        self.article_ttl_days = 7
        self.query_ttl_hours = 24

    def _hash_string(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
        
    def _normalize_query(self, query: str) -> str:
        return query.strip().lower()

    def get_cached_article(self, url: str) -> ArticleCache | None:
        url_hash = self._hash_string(url)
        stmt = select(ArticleCache).where(
            ArticleCache.url_hash == url_hash,
            ArticleCache.expires_at > datetime.now(timezone.utc)
        )
        cached = self.session.execute(stmt).scalar_one_or_none()
        if cached:
            logger.info("Article cache hit", url=url)
        return cached

    def set_cached_article(self, url: str, canonical_url: str, domain: str, title: str, body: str, published_at: datetime | None, embedding_vector: list[float] | None = None) -> ArticleCache:
        url_hash = self._hash_string(url)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.article_ttl_days)
        
        stmt = select(ArticleCache).where(ArticleCache.url_hash == url_hash)
        cached = self.session.execute(stmt).scalar_one_or_none()
        
        if cached:
            cached.title = title
            cached.body = body
            cached.published_at = published_at
            cached.embedding_vector = embedding_vector
            cached.expires_at = expires_at
        else:
            cached = ArticleCache(
                url_hash=url_hash,
                url_canonical=canonical_url,
                domain=domain,
                title=title,
                body=body,
                published_at=published_at,
                embedding_vector=embedding_vector,
                expires_at=expires_at
            )
            self.session.add(cached)
            
        self.session.commit()
        return cached

    def get_cached_query(self, query: str) -> AnalysisResult | None:
        norm_query = self._normalize_query(query)
        query_hash = self._hash_string(norm_query)
        
        stmt = select(QueryCache).where(
            QueryCache.query_hash == query_hash,
            QueryCache.expires_at > datetime.now(timezone.utc)
        )
        cached = self.session.execute(stmt).scalar_one_or_none()
        
        if cached and cached.analysis_result_id:
            logger.info("Query cache hit", query=query)
            analysis_stmt = select(AnalysisResult).where(AnalysisResult.id == cached.analysis_result_id)
            return self.session.execute(analysis_stmt).scalar_one_or_none()
            
        return None

    def set_cached_query(self, query: str, analysis_result_id: int) -> QueryCache:
        norm_query = self._normalize_query(query)
        query_hash = self._hash_string(norm_query)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.query_ttl_hours)
        
        stmt = select(QueryCache).where(QueryCache.query_hash == query_hash)
        cached = self.session.execute(stmt).scalar_one_or_none()
        
        if cached:
            cached.analysis_result_id = analysis_result_id
            cached.expires_at = expires_at
        else:
            cached = QueryCache(
                query_hash=query_hash,
                query_text=norm_query,
                analysis_result_id=analysis_result_id,
                expires_at=expires_at
            )
            self.session.add(cached)
            
        self.session.commit()
        return cached
