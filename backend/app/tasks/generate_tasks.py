"""Celery tasks for generating neutral news from validated facts."""

from datetime import datetime, timezone
import structlog
from sqlalchemy import select, update

from app.celery_app import celery_app
from app.models.domain import Article, StructuredFact, GeneratedNews, FactTraceability, ArticleStatus
from app.tasks._celery_infra import SyncSessionLocal, run_async, get_ai_provider

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=1)
def generate_news_from_articles(self, articles_ids: list[int], provider_name: str = "openai", encrypted_api_key: str | None = None, language: str = "es"):
    """
    Generate neutral news from a list of successfully analyzed article IDs.
    """
    logger.info("Starting news generation", article_ids=articles_ids)
    
    with SyncSessionLocal() as session:
        # 1. Verification of state
        articles = session.execute(
            select(Article).where(Article.id.in_(articles_ids), Article.status == ArticleStatus.ANALYZED)
        ).scalars().all()
        
        if not articles:
            logger.error("No valid ANALYZED articles found for generation", ids=articles_ids)
            return {"status": "error", "message": "Articles not found or not in ANALYZED state"}
            
        # 2. Get Facts
        facts = session.execute(
            select(StructuredFact).where(StructuredFact.article_id.in_([a.id for a in articles]), StructuredFact.type == "FACT", StructuredFact.chunk_index == 0)
        ).scalars().all()
        
        if not facts:
            logger.error("No consolidated facts found in articles", ids=articles_ids)
            return {"status": "error", "message": "No consolidated facts available for generation"}
            
    # 3. Inter-domain Fact Association (cross-reference facts using DBSCAN)
    from app.services.ai.clustering import FactAssociator
    associator = FactAssociator()
    clusters = associator.group_facts(list(facts), eps=0.5)
    
    # Calculate initial reliability score dynamically based on cross-domain consistency
    # (How many sources agreed on facts vs how many total unique facts were found)
    # Simple metric: Ratio of facts confirmed by >1 source vs total clusters
    consensus_clusters = 0
    total_clusters = len(clusters)
    for cluster in clusters:
        unique_sources = len(set(f.article_id for f in cluster))
        if unique_sources > 1:
            consensus_clusters += 1
            
    # Base score
    dynamic_score = (consensus_clusters / total_clusters) * 100 if total_clusters > 0 else 0
    
    # 4. Filter or organize facts. For now, pass all clustered fact statements to AI.
    # Group them so AI sees the consensus weight.
    grouped_fact_texts = []
    
    fact_id_map = {} # Keep track of which model id corresponds to what text to link traceability later
    list_idx = 1
    
    for cluster in clusters:
        # Take the content of the first fact in cluster as representative
        rep_fact = cluster[0]
        sources = [f"Source Article {f.article_id}" for f in cluster]
        grouped_fact_texts.append(f"[{list_idx}] Fact: {rep_fact.content} (Confirmed by: {', '.join(set(sources))})")
        
        # We store the mapping so when the AI quotes "[1]", we know it used these fact DB ids.
        fact_id_map[list_idx] = [f.id for f in cluster]
        list_idx += 1
        
    # 5. Build prompt
    lang_instruction = "Respond ONLY IN SPANISH." if language == "es" else "Respond ONLY IN ENGLISH."
    prompt = (
        "Based strictly on the following consolidated facts, generate a neutral and objective news article.\n"
        "STRICT RULES:\n"
        "1. Do not assume or invent anything that is not in the list.\n"
        "2. Use brackets to reference the bibliographic citations of the facts used, example: 'The event occurred [1] and [2].'\n"
        "3. Structure the JSON with the exact keys below.\n"
        f"⚠️ LANGUAGE INSTRUCTION: {lang_instruction}\n\n"
        f"FACTS:\n" + "\n".join(grouped_fact_texts) + "\n\n"
        "JSON Structure (Only return the valid JSON):\n"
        "{\n"
        '  "title": "An objective and neutral headline",\n'
        '  "lead": "The first paragraph summarizing the core facts (answer what, who, when, where).",\n'
        '  "body": "The main body detailing the facts, always citing in brackets [X] the facts used."\n'
        "}"
    )
    
    provider = get_ai_provider(provider_name, encrypted_api_key, language=language)
    response = run_async(provider.analyze(prompt, max_tokens=2000))
    
    # Parse JSON
    import json
    text = response.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
        
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON for news generation", response=text[:200])
        import re
        title = provider._extract_json_string_value(text, "title") or "Noticia Generada"
        lead = provider._extract_json_string_value(text, "lead") or ""
        body = provider._extract_json_string_value(text, "body") or text
        parsed = {"title": title, "lead": lead, "body": body}
        
    # Extract citations to build traceability
    import re
    citations = set()
    all_text = parsed.get("lead", "") + " " + parsed.get("body", "")
    for match in re.finditer(r'\[(\d+)\]', all_text):
        try:
            citations.add(int(match.group(1)))
        except ValueError:
            pass
            
    # 6. Save strictly to DB
    with SyncSessionLocal() as session:
        news = GeneratedNews(
            title=parsed.get("title", ""),
            lead=parsed.get("lead", ""),
            body=parsed.get("body", ""),
            context_articles_ids=articles_ids,
            reliability_score_achieved=dynamic_score,
            has_new_context_available=False
        )
        session.add(news)
        session.flush() # get ID
        
        # Link traceability
        # For every cited [X] in the AI's response, link all corresponding StructuredFact IDs
        linked_fact_ids = set()
        for cit in citations:
            if cit in fact_id_map:
                linked_fact_ids.update(fact_id_map[cit])
                
        for fact_id in linked_fact_ids:
            trace = FactTraceability(
                generated_news_id=news.id,
                structured_fact_id=fact_id
            )
            session.add(trace)
            
        session.commit()
        news_id = news.id
        
    logger.info("News generated and saved successfully", news_id=news_id)
    return {"status": "completed", "news_id": news_id}

@celery_app.task
def check_new_context_availability(article_id: int):
    """
    Checks if a newly analyzed article provides relevant new context for any existing GeneratedNews.
    Marks has_new_context_available = True if similarity > threshold.
    """
    logger.info("Checking for new context availability", article_id=article_id)
    with SyncSessionLocal() as session:
        # Get all facts from the newly analyzed article
        new_facts = session.execute(
            select(StructuredFact).where(
                StructuredFact.article_id == article_id, 
                StructuredFact.type == "FACT",
                StructuredFact.embedding != None
            )
        ).scalars().all()
        
        if not new_facts:
            return
            
        affected_news_ids = set()
        for fact in new_facts:
            # Find any GeneratedNews whose source facts match this new fact closely (cosine distance < 0.2 => similarity > 0.8)
            stmt = select(GeneratedNews).distinct().join(
                FactTraceability, FactTraceability.generated_news_id == GeneratedNews.id
            ).join(
                StructuredFact, StructuredFact.id == FactTraceability.structured_fact_id
            ).filter(
                StructuredFact.embedding.cosine_distance(fact.embedding) < 0.2,
                ~GeneratedNews.context_articles_ids.contains([article_id]),
                GeneratedNews.has_new_context_available == False
            )
            
            matching_news = session.execute(stmt).scalars().all()
            for n in matching_news:
                n.has_new_context_available = True
                affected_news_ids.add(n.id)
                
        if affected_news_ids:
            session.commit()
            logger.info("New context flag set for existing GeneratedNews", count=len(affected_news_ids), news_ids=list(affected_news_ids))
