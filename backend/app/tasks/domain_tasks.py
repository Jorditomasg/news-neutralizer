from datetime import datetime, timezone
import structlog
from urllib.parse import urlparse

from app.celery_app import celery_app
from app.models.domain import SourceDomain
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Wait, `_get_ai_provider` is in `search_tasks.py`, we should reuse it or put it in a shared place.
# For now, I'll import AIProviderFactory directly.
from app.services.ai.factory import AIProviderFactory

logger = structlog.get_logger(__name__)

# Sync engine for Celery (fork-safe)
_sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
SyncSessionLocal = sessionmaker(bind=_sync_engine)


def _run_async(coro):
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def extract_domain(url: str) -> str:
    """Extracts the base domain (e.g., 'elmundo.es') from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def discover_and_evaluate_domains(self, urls: list[str], provider_name: str = "openai", encrypted_api_key: str | None = None):
    """
    Takes a list of URLs, extracts domains, checks if they are new,
    and runs the AI evaluation on new ones to assign a trust score.
    """
    domains = set()
    for url in urls:
        d = extract_domain(url)
        if d:
            domains.add(d)

    untracked = []
    with SyncSessionLocal() as session:
        for domain in domains:
            # Check if it exists
            stmt = select(SourceDomain).where(SourceDomain.domain == domain)
            result = session.execute(stmt).scalar_one_or_none()
            
            if not result:
                # Add as untracked, pending evaluation
                new_dom = SourceDomain(domain=domain, is_evaluated=False)
                session.add(new_dom)
                untracked.append(domain)
        session.commit()

    if not untracked:
        logger.info("No new domains to evaluate")
        return

    # For each new domain, trigger an evaluation
    from app.core.security import decrypt_api_key
    
    api_key = None
    if encrypted_api_key:
        api_key = decrypt_api_key(encrypted_api_key)
        
    provider = AIProviderFactory.get(provider_name, api_key=api_key)
    
    for domain in untracked:
        try:
            logger.info("Evaluating domain trust", domain=domain)
            # We ask the AI to evaluate the credibility of the domain.
            # Using generic knowledge since this is a known URL.
            prompt = (
                f"Analiza la credibilidad periodística y el sesgo editorial del dominio web: '{domain}'.\n\n"
                "Instrucciones:\n"
                "1. Si el dominio es un medio de comunicación establecido, asígnale un trust_score alto (70-100).\n"
                "2. Si es un agregador genérico (yahoo, msn), dale un trust_score medio (50-70).\n"
                "3. Si es un blog personal, página satírica, fuente de desinformación conocida o hiper-partidista sin rigor, asígnale un trust_score bajo (0-40).\n"
                "4. Si NO CONOCES el dominio, dale un trust_score conservador de 40.\n\n"
                "Responde SOLO con JSON válido con esta estructura:\n"
                "{\n"
                '  "trust_score": un número de 0 a 100,\n'
                '  "bias_lean": "left", "center-left", "center", "center-right", "right", "extreme", "unknown",\n'
                '  "reasoning": "Explicación muy breve de por qué."\n'
                "}"
            )
            
            response_text = _run_async(provider.analyze(prompt, max_tokens=150))
            
            # Parse the JSON response
            import json
            # basic clean
            clean_res = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_res)
            
            trust_score = int(data.get("trust_score", 40))
            bias = str(data.get("bias_lean", "unknown"))
            reasoning = str(data.get("reasoning", "Sin datos"))
            
            with SyncSessionLocal() as session:
                stmt = update(SourceDomain).where(SourceDomain.domain == domain).values(
                    is_evaluated=True,
                    trust_score=trust_score,
                    bias_lean=bias,
                    ai_reasoning=reasoning,
                    evaluated_at=datetime.now(timezone.utc)
                )
                session.execute(stmt)
                session.commit()
                logger.info("Domain evaluated", domain=domain, score=trust_score, bias=bias)
                
        except Exception as e:
            logger.error("Failed to evaluate domain", domain=domain, error=str(e))
