import structlog
from app.models.domain import SourceDomain
from app.tasks.domain_tasks import extract_domain
from app.tasks.search_tasks import SyncSessionLocal # reuse the sync session maker
from sqlalchemy import select

logger = structlog.get_logger(__name__)

class DomainFilter:
    """
    Filters search hits against the domain trust database.
    """
    
    def __init__(self, min_trust_score: int = 40):
        self.min_trust_score = min_trust_score

    def filter_untrusted_hits(self, hits: list) -> list:
        """
        Takes a list of ArticleHits and removes any that belong to a domain
        which has already been evaluated and scored below the trust threshold.
        """
        if not hits:
            return hits
            
        filtered = []
        domains_to_check = set(extract_domain(h.url) for h in hits)
        
        # Load known bad domains in one query
        bad_domains = set()
        with SyncSessionLocal() as session:
            stmt = select(SourceDomain.domain).where(
                SourceDomain.domain.in_(domains_to_check),
                SourceDomain.is_evaluated == True,
                SourceDomain.trust_score < self.min_trust_score
            )
            results = session.execute(stmt).scalars().all()
            for r in results:
                bad_domains.add(r)
                
        for hit in hits:
            domain = extract_domain(hit.url)
            if domain in bad_domains:
                logger.info("Discarding hit from low-trust domain", domain=domain, title=hit.title[:40])
                continue
            filtered.append(hit)
            
        return filtered
