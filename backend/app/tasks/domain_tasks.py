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
def discover_and_evaluate_domains(self, urls: list[str], provider_name: str = "openai", encrypted_api_key: str | None = None, language: str = "es"):
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
    
    provider = get_ai_provider(provider_name, encrypted_api_key, language=language)
    
    domains_list = ", ".join(f"'{d}'" for d in untracked)
    lang_instruction = "Respond ONLY IN SPANISH." if language == "es" else "Respond ONLY IN ENGLISH."
    prompt = (
        f"Analyze the journalistic credibility and editorial bias of the following web domains: {domains_list}.\n\n"
        "Instructions:\n"
        "1. If the domain is an established media outlet, assign it a high trust_score (70-100).\n"
        "2. If it is a generic aggregator (yahoo, msn), give it a medium trust_score (50-70).\n"
        "3. If it is a personal blog, satirical page, known disinformation source, or hyper-partisan without rigor, assign a low trust_score (0-40).\n"
        "4. If you DO NOT KNOW the domain, give it a conservative trust_score of 40.\n\n"
        f"⚠️ LANGUAGE INSTRUCTION: {lang_instruction}\n"
        "Respond ONLY with a valid JSON array with an object for each domain:\n"
        "[\n"
        "  {\n"
        '    "domain": "example.com",\n'
        '    "trust_score": a number from 0 to 100,\n'
        '    "bias_lean": "left" | "center-left" | "center" | "center-right" | "right" | "extreme" | "unknown",\n'
        '    "reasoning": "Very brief explanation."\n'
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
            
            # Calculate reliability scores for all newly evaluated domains
            from app.services.reliability import update_domain_reliability
            for domain in untracked:
                update_domain_reliability(session, domain)
            
    except Exception as e:
        logger.error("Batch domain evaluation failed, falling back to individual", error=str(e))
        # Fallback: evaluate one by one
        for domain in untracked:
            try:
                single_prompt = (
                    f"Analyze the journalistic credibility and editorial bias of the web domain: '{domain}'.\n\n"
                    f"⚠️ LANGUAGE INSTRUCTION: {lang_instruction}\n"
                    "Respond ONLY with valid JSON:\n"
                    '{"trust_score": number 0-100, "bias_lean": "center|left|right|unknown", "reasoning": "brief explanation"}'
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
