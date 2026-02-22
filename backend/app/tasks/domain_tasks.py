from datetime import datetime, timezone
import structlog
from urllib.parse import urlparse

from app.celery_app import celery_app
from app.models.domain import SourceDomain
from sqlalchemy import select, update
from app.tasks._celery_infra import SyncSessionLocal, run_async, get_ai_provider

logger = structlog.get_logger(__name__)



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

    # Batch-evaluate all new domains in a single LLM call
    import json
    
    provider = get_ai_provider(provider_name, encrypted_api_key)
    
    domains_list = ", ".join(f"'{d}'" for d in untracked)
    prompt = (
        f"Analiza la credibilidad periodística y el sesgo editorial de los siguientes dominios web: {domains_list}.\n\n"
        "Instrucciones:\n"
        "1. Si el dominio es un medio de comunicación establecido, asígnale un trust_score alto (70-100).\n"
        "2. Si es un agregador genérico (yahoo, msn), dale un trust_score medio (50-70).\n"
        "3. Si es un blog personal, página satírica, fuente de desinformación conocida o hiper-partidista sin rigor, asígnale un trust_score bajo (0-40).\n"
        "4. Si NO CONOCES el dominio, dale un trust_score conservador de 40.\n\n"
        "Responde SOLO con un JSON array válido con un objeto por cada dominio:\n"
        "[\n"
        "  {\n"
        '    "domain": "ejemplo.com",\n'
        '    "trust_score": un número de 0 a 100,\n'
        '    "bias_lean": "left" | "center-left" | "center" | "center-right" | "right" | "extreme" | "unknown",\n'
        '    "reasoning": "Explicación muy breve."\n'
        "  }\n"
        "]\n"
    )
    
    try:
        logger.info("Batch evaluating domains", count=len(untracked), domains=untracked)
        response_text = run_async(provider.analyze(prompt, max_tokens=200 * len(untracked)))
        
        # Parse the JSON array response
        clean_res = response_text.replace("```json", "").replace("```", "").strip()
        evaluations = json.loads(clean_res)
        
        if not isinstance(evaluations, list):
            evaluations = [evaluations]
        
        # Map evaluations by domain name
        eval_map = {}
        for ev in evaluations:
            d = ev.get("domain", "").lower().strip()
            if d:
                eval_map[d] = ev
        
        # Update DB in batch
        with SyncSessionLocal() as session:
            for domain in untracked:
                ev = eval_map.get(domain, {})
                trust_score = int(ev.get("trust_score", 40))
                bias = str(ev.get("bias_lean", "unknown"))
                reasoning = str(ev.get("reasoning", "Sin datos"))
                
                stmt = update(SourceDomain).where(SourceDomain.domain == domain).values(
                    is_evaluated=True,
                    trust_score=trust_score,
                    bias_lean=bias,
                    ai_reasoning=reasoning,
                    evaluated_at=datetime.now(timezone.utc)
                )
                session.execute(stmt)
                logger.info("Domain evaluated", domain=domain, score=trust_score, bias=bias)
            session.commit()
            
    except Exception as e:
        logger.error("Batch domain evaluation failed, falling back to individual", error=str(e))
        # Fallback: evaluate one by one
        for domain in untracked:
            try:
                single_prompt = (
                    f"Analiza la credibilidad periodística y el sesgo editorial del dominio web: '{domain}'.\n\n"
                    "Responde SOLO con JSON válido:\n"
                    '{"trust_score": número 0-100, "bias_lean": "center|left|right|unknown", "reasoning": "breve"}'
                )
                response_text = run_async(provider.analyze(single_prompt, max_tokens=150))
                clean_res = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_res)
                
                with SyncSessionLocal() as session:
                    stmt = update(SourceDomain).where(SourceDomain.domain == domain).values(
                        is_evaluated=True,
                        trust_score=int(data.get("trust_score", 40)),
                        bias_lean=str(data.get("bias_lean", "unknown")),
                        ai_reasoning=str(data.get("reasoning", "Sin datos")),
                        evaluated_at=datetime.now(timezone.utc)
                    )
                    session.execute(stmt)
                    session.commit()
            except Exception as inner_e:
                logger.error("Failed to evaluate domain", domain=domain, error=str(inner_e))
