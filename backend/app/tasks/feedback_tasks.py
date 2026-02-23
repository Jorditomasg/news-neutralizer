"""Celery tasks for processing user feedback asynchronously."""

import structlog
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.tasks._celery_infra import SyncSessionLocal
from app.models.domain import Feedback, Article, AnalysisResult, SourceDomain

logger = structlog.get_logger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_feedback_async(self, feedback_id: int):
    """
    Process a single feedback entry and adjust heuristic weights globally.
    """
    logger.info("Processing feedback asynchronously", feedback_id=feedback_id)
    
    with SyncSessionLocal() as session:
        stmt = select(Feedback).where(Feedback.id == feedback_id)
        feedback = session.execute(stmt).scalar_one_or_none()
        
        if not feedback:
            logger.warning("Feedback not found", feedback_id=feedback_id)
            return
            
        if feedback.target_type == "article":
            _process_article_feedback(session, feedback)
        elif feedback.target_type == "analysis":
            _process_analysis_feedback(session, feedback)
        elif feedback.target_type == "domain":
            _process_domain_feedback(session, feedback)

def _process_article_feedback(session: Session, feedback: Feedback):
    """
    If an article is disliked, penalize its source domain's trust score slightly.
    """
    if feedback.vote != "dislike":
        return
        
    try:
        article_id = int(feedback.target_id)
    except ValueError:
        return
        
    stmt = select(Article).where(Article.id == article_id)
    article = session.execute(stmt).scalar_one_or_none()
    
    if not article:
        return
        
    source_name = article.source_name
    
    # Simple logic: Every 5 dislikes on articles of the same domain drops trust_score by 1
    # Check total dislikes for articles from this domain
    # This involves joining Feedback with Article where Article.source_name == source_name
    # To keep it performant and simple for now, we just decrement directly on the SourceDomain if evaluated
    
    domain_stmt = select(SourceDomain).where(SourceDomain.domain.ilike(f"%{source_name}%"))
    domain_entry = session.execute(domain_stmt).scalar_one_or_none()
    
    if domain_entry and domain_entry.trust_score is not None:
        new_score = max(0, domain_entry.trust_score - 1)
        domain_entry.trust_score = new_score
        logger.info("Penalized domain trust score based on article dislike", domain=domain_entry.domain, new_score=new_score)
        session.commit()
        # Recalculate reliability score
        from app.services.reliability import update_domain_reliability
        update_domain_reliability(session, domain_entry.domain)

def _process_analysis_feedback(session: Session, feedback: Feedback):
    """
    If a full analysis is disliked, we could flag it to tune semantic thresholds.
    """
    if feedback.vote != "dislike":
        return
        
    logger.info("Analysis received dislike, marking for review", analysis_id=feedback.target_id)
    # Implement threshold tuning logic here in the future
    # Currently handled conceptually: The backend admin can see these and manually adjust or we can build an auto-tuner.

def _process_domain_feedback(session: Session, feedback: Feedback):
    """
    Direct feedback on a domain.
    """
    domain_name = str(feedback.target_id)
    domain_stmt = select(SourceDomain).where(SourceDomain.domain == domain_name)
    domain_entry = session.execute(domain_stmt).scalar_one_or_none()
    
    if domain_entry and domain_entry.trust_score is not None:
        delta = -5 if feedback.vote == "dislike" else 5 if feedback.vote == "like" else 0
        new_score = max(0, min(100, domain_entry.trust_score + delta))
        domain_entry.trust_score = new_score
        logger.info("Adjusted domain trust score from direct feedback", domain=domain_name, delta=delta, new_score=new_score)
        session.commit()
        # Recalculate reliability score
        from app.services.reliability import update_domain_reliability
        update_domain_reliability(session, domain_name)
