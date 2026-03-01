import asyncio
import sys
import os
import structlog

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, delete
from app.core.database import SessionLocal
from app.models import Article, SearchTask, AnalysisResult
from app.models.domain import ArticleStatus
from app.services.scraper.url_utils import normalize_url

logger = structlog.get_logger()

async def deduplicate():
    async with SessionLocal() as db:
        print("Loading source articles...")
        # Load all source articles
        stmt = select(Article).where(
            Article.is_source == True, 
            Article.status == ArticleStatus.ANALYZED
        ).order_by(Article.created_at.asc())
        
        result = await db.execute(stmt)
        articles = result.scalars().all()
        
        groups = {}
        for article in articles:
            norm_url = normalize_url(article.source_url)
            groups.setdefault(norm_url, []).append(article)
            
        print(f"Found {len(articles)} analyzed source articles across {len(groups)} unique URLs.")
        
        duplicates_removed = 0
        tasks_redirected = 0
        
        for norm_url, group in groups.items():
            keep_article = group[0]
            
            # If the URL is not fully normalized in DB, update it
            if keep_article.source_url != norm_url:
                keep_article.source_url = norm_url
                # Also update its task
                keep_task = (await db.execute(select(SearchTask).where(SearchTask.id == keep_article.search_task_id))).scalar_one_or_none()
                if keep_task:
                    keep_task.source_url = norm_url
                    
            if len(group) > 1:
                print(f"Deduping URL: {norm_url} ({len(group)} instances)")
                
                # We need keep_task.task_id for the redirect
                keep_task = (await db.execute(select(SearchTask).where(SearchTask.id == keep_article.search_task_id))).scalar_one()
                
                for dup in group[1:]:
                    dup_task = (await db.execute(select(SearchTask).where(SearchTask.id == dup.search_task_id))).scalar_one_or_none()
                    
                    if dup_task:
                        # Convert to redirect task
                        dup_task.status = "redirected"
                        dup_task.progress_message = keep_task.task_id
                        
                        # Delete its analysis result
                        await db.execute(delete(AnalysisResult).where(AnalysisResult.search_task_id == dup_task.id))
                        
                        # Delete all articles inside this task (this will also cascade delete StructuredFacts)
                        await db.execute(delete(Article).where(Article.search_task_id == dup_task.id))
                        
                        tasks_redirected += 1
                        duplicates_removed += 1
                        
        print("Committing changes to database...")
        await db.commit()
        print(f"Done! Redirected {tasks_redirected} tasks and removed {duplicates_removed} duplicate sets of records.")

if __name__ == "__main__":
    asyncio.run(deduplicate())
