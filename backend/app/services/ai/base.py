"""Abstract base class for AI providers (Strategy Pattern)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import re
import structlog

logger = structlog.get_logger()


@dataclass
class AnalysisResult:
    """Structured result from AI analysis."""

    topic_summary: str
    objective_facts: list[str]
    bias_elements: list[dict]
    neutralized_article: dict
    source_bias_scores: dict[str, dict]
    tokens_used: int | None = None

@dataclass
class ExtractedFactsResult:
    """Structured facts extracted from a single text chunk."""
    facts: list[str]
    unverified_claims: list[str]
    biases: list[dict]
    framing: list[str]
    entities: list[str]
    tone: str


class AIProvider(ABC):
    """
    Abstract interface for AI/LLM providers.

    Implementations: OpenAIProvider, AnthropicProvider, GoogleProvider, OllamaProvider.
    Each provider must implement all abstract methods.
    """

    def __init__(self, api_key: str | None = None, language: str = "es", summary_length: str = "medium", bias_strictness: str = "standard"):
        self.api_key = api_key
        self.language = language
        self.summary_length = summary_length
        self.bias_strictness = bias_strictness

    # ── Language helpers ───────────────────────────────────────

    #: Maps ISO 639-1 codes to English language names used in AI prompts.
    #: Extend this dict when adding support for new locales.
    LANGUAGE_NAMES: dict[str, str] = {
        "es": "Spanish",
        "en": "English",
        "it": "Italian",
        "fr": "French",
        "de": "German",
        "pt": "Portuguese",
        "ca": "Catalan",
        "nl": "Dutch",
        "pl": "Polish",
        "ru": "Russian",
        "zh": "Chinese",
        "ja": "Japanese",
        "ar": "Arabic",
    }

    def _lang_instruction(self) -> str:
        """Return a language instruction sentence for AI prompts based on `self.language`."""
        name = self.LANGUAGE_NAMES.get(self.language, f"the language with ISO code '{self.language}'")
        return f"Respond strictly in {name}."

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier for this provider (e.g., 'openai', 'anthropic')."""
        ...

    @abstractmethod
    async def analyze(self, prompt: str, max_tokens: int = 4000) -> str:
        """Send a prompt and return the raw LLM response text."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @abstractmethod
    def validate_key(self) -> bool:
        """Check if the configured API key is valid (format check, not live call)."""
        ...

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate the cost in USD for a given token count."""
        ...

    async def extract_facts_from_chunk(self, chunk: str) -> "ExtractedFactsResult":
        """Extract structured facts and bias info from a chunk of text."""
        lang_instruction = self._lang_instruction()

        bias_map = {
            "standard": "Filter it and only return extremely obvious and severe biases.",
            "strict": "Detect absolutely all manipulation tactics: framing, victimization, adjectivation, and mild partisan jargon.",
        }
        bias_instruction = bias_map.get(self.bias_strictness, bias_map["standard"])

        prompt = (
            "Analyze the following journalistic text snippet and meticulously extract "
            "the required information in strict JSON format. "
            "Your analysis must be completely exhaustive and atomic.\n"
            f"⚠️ LANGUAGE INSTRUCTION: {lang_instruction}\n"
            f"⚠️ BIAS STRICTNESS: {bias_instruction}\n"
            "⚠️ IMPORTANT: If the text is very short or seems cut off (e.g., paywall), "
            "extract the available facts no matter how minimal. DO NOT return empty lists if there is at least one fact in the text.\n"
            "⚠️ IMPORTANT: If there are no bias elements, unverified claims, or framing, return an empty list `[]`. DO NOT return empty objects like `[{\"type\": \"\", \"quote\": \"\", \"explanation\": \"\"}]`.\n\n"
            f"TEXT:\n{chunk}\n\n"
            "Respond ONLY with a valid JSON object containing exactly these keys:\n"
            "{\n"
            '  "facts": ["List of verifiable facts or concrete actions that occurred. Each must be an independent and atomic statement."],\n'
            '  "unverified_claims": ["Claims or quotes from sources that are not consolidated facts. Use [] if there are none."],\n'
            '  "biases": [\n'
            '    {\n'
            '      "type": "type of bias (sensationalism, adjectivation, victimization, etc.)",\n'
            '      "quote": "exact exact quote where it is seen",\n'
            '      "explanation": "brief explanation"\n'
            '    }\n'
            '  ], // Use [] if there is no clear bias.\n'
            '  "framing": ["Brief description of how the news is being framed. Use [] if not applicable."],\n'
            '  "entities": ["List of key proper names, organizations, roles, or places mentioned."],\n'
            '  "tone": "A single word defining the overall tone (e.g., alarmist, neutral, critical, empathetic)."\n'
            "}"
        )
        response = await self.analyze(prompt, max_tokens=2000)
        parsed = self._parse_extracted_facts(response)
        
        return ExtractedFactsResult(
            facts=parsed.get("facts", []),
            unverified_claims=parsed.get("unverified_claims", []),
            biases=parsed.get("biases", []),
            framing=parsed.get("framing", []),
            entities=parsed.get("entities", []),
            tone=parsed.get("tone", "desconocido")
        )

    async def consolidate_intra_article_facts(self, facts: list[str]) -> list[str]:
        """Deduplicate and consolidate a list of facts from the same article."""
        if not facts:
            return []
            
        lang_instruction = self._lang_instruction()
        facts_text = "\n".join([f"- {f}" for f in facts])
        prompt = (
            "Below is a list of facts extracted from different snippets "
            "of the same journalistic article. Your task is to remove exact duplicates "
            "or redundancies, combining information if necessary, to produce a "
            "consolidated, atomic, and exhaustive list of facts.\n"
            f"⚠️ LANGUAGE INSTRUCTION: {lang_instruction}\n\n"
            f"ORIGINAL FACTS:\n{facts_text}\n\n"
            "Respond ONLY with a valid JSON object containing the key 'consolidated_facts' "
            "whose value is a list of strings with the consolidated facts.\n"
            "Example response format:\n"
            "{\n"
            '  "consolidated_facts": [\n'
            '    "Fact 1",\n'
            '    "Fact 2"\n'
            '  ]\n'
            "}"
        )
        response = await self.analyze(prompt, max_tokens=3000)
        
        # Parse JSON
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        try:
            parsed = json.loads(text)
            return parsed.get("consolidated_facts", facts)
        except json.JSONDecodeError:
            # regex fallback
            extracted = self._extract_json_array(text, "consolidated_facts")
            return extracted if extracted else facts

    # ── Robust JSON extraction ──────────────────────────────────

    @staticmethod
    def _extract_json_string_value(text: str, key: str) -> str | None:
        """Extract a JSON string value for a given key, handling escaped chars."""
        pattern = rf'"{key}"\s*:\s*"'
        match = re.search(pattern, text)
        if not match:
            return None

        start = match.end()
        result_chars = []
        i = start
        while i < len(text):
            ch = text[i]
            if ch == '\\' and i + 1 < len(text):
                next_ch = text[i + 1]
                if next_ch == 'n':
                    result_chars.append('\n')
                elif next_ch == 't':
                    result_chars.append('\t')
                elif next_ch == '"':
                    result_chars.append('"')
                elif next_ch == '\\':
                    result_chars.append('\\')
                else:
                    result_chars.append(next_ch)
                i += 2
                continue
            if ch == '"':
                # End of string
                return ''.join(result_chars)
            result_chars.append(ch)
            i += 1

        # String was truncated — return what we have
        return ''.join(result_chars)

    @staticmethod
    def _extract_json_array(text: str, key: str) -> list | None:
        """Extract a JSON array value for a given key. Returns complete items only."""
        pattern = rf'"{key}"\s*:\s*\['
        match = re.search(pattern, text)
        if not match:
            return None

        start = match.end()
        # Find the matching closing bracket
        depth = 1
        i = start
        in_str = False
        while i < len(text) and depth > 0:
            ch = text[i]
            if ch == '\\' and in_str:
                i += 2
                continue
            if ch == '"':
                in_str = not in_str
            elif not in_str:
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
            i += 1

        array_content = text[start:i - 1] if depth == 0 else text[start:]

        # For string arrays: extract individual strings
        if key == "objective_facts":
            facts = []
            for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', array_content):
                fact = m.group(1).replace('\\"', '"').replace('\\n', '\n')
                facts.append(fact)
            return facts

        # For object arrays (bias_elements): extract complete objects
        items = []
        brace_depth = 0
        obj_start = None
        in_string = False
        for idx in range(len(array_content)):
            ch = array_content[idx]
            if ch == '\\' and in_string:
                continue
            if ch == '"' and (idx == 0 or array_content[idx - 1] != '\\'):
                in_string = not in_string
            elif not in_string:
                if ch == '{':
                    if brace_depth == 0:
                        obj_start = idx
                    brace_depth += 1
                elif ch == '}':
                    brace_depth -= 1
                    if brace_depth == 0 and obj_start is not None:
                        obj_str = array_content[obj_start:idx + 1]
                        try:
                            items.append(json.loads(obj_str))
                        except json.JSONDecodeError:
                            pass
                        obj_start = None
        return items

    @staticmethod
    def _extract_json_object(text: str, key: str) -> dict | None:
        """Extract a JSON object value for a given key."""
        pattern = rf'"{key}"\s*:\s*\{{'
        match = re.search(pattern, text)
        if not match:
            return None

        start = match.start() + len(match.group()) - 1  # at the '{'
        depth = 0
        in_str = False
        i = start
        while i < len(text):
            ch = text[i]
            if ch == '\\' and in_str:
                i += 2
                continue
            if ch == '"':
                in_str = not in_str
            elif not in_str:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        obj_str = text[start:i + 1]
                        try:
                            return json.loads(obj_str)
                        except json.JSONDecodeError:
                            return None
            i += 1
        return None

    def _parse_response(self, response: str) -> AnalysisResult:
        """
        Parse the AI response into an AnalysisResult.
        Uses multiple strategies: direct JSON parse, then regex field extraction.
        """
        # Strip markdown code blocks if present
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        # Strategy 1: Try direct JSON parse (ideal case)
        try:
            data = json.loads(text)
            logger.info("AI response parsed directly as valid JSON")
            return AnalysisResult(
                topic_summary=data.get("topic_summary", ""),
                objective_facts=data.get("objective_facts", []),
                bias_elements=data.get("bias_elements", []),
                neutralized_article=data.get("neutralized_article", {"title": "Error", "content": "N/A"}),
                source_bias_scores=data.get("source_bias_scores", {}),
            )
        except json.JSONDecodeError:
            logger.warning("Direct JSON parse failed, using regex extraction")

        # Strategy 2: Extract fields individually with regex (handles truncation)
        topic = self._extract_json_string_value(text, "topic_summary") or ""
        facts = self._extract_json_array(text, "objective_facts") or []
        bias = self._extract_json_array(text, "bias_elements") or []
        neutralized = self._extract_json_object(text, "neutralized_article") or {"title": "Recuperado", "content": ""}
        scores = self._extract_json_object(text, "source_bias_scores") or {}

        # Check if we got anything useful
        has_content = bool(topic or facts or bias or neutralized.get("content"))
        if has_content:
            logger.info(
                "Extracted partial AI response",
                topic_len=len(topic),
                facts_count=len(facts),
                bias_count=len(bias),
                has_scores=bool(scores),
            )
            return AnalysisResult(
                topic_summary=topic,
                objective_facts=facts,
                bias_elements=bias,
                neutralized_article=neutralized,
                source_bias_scores=scores,
            )

        # Nothing could be parsed
        logger.error("Could not extract any fields from AI response",
                      response_preview=text[:300])
        return AnalysisResult(
            topic_summary="No se pudo procesar la respuesta de la IA",
            objective_facts=[],
            bias_elements=[],
            neutralized_article={"title": "Error de Procesamiento", "content": text[:2000]},
            source_bias_scores={},
        )

    async def analyze_articles(self, articles: list[dict]) -> AnalysisResult:
        """
        Analyze a set of articles for bias and generate a neutralized summary.
        """
        prompt = self._build_analysis_prompt(articles)
        response = await self.analyze(prompt, max_tokens=4096)
        return self._parse_response(response)

    def _parse_extracted_facts(self, response: str) -> dict:
        """Parse JSON response from the chunk extraction prompt."""
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse extracted facts JSON directly, using regex...", response_preview=text[:200])
            
            # regex fallback
            facts = self._extract_json_array(text, "facts") or []
            claims = self._extract_json_array(text, "unverified_claims") or []
            biases = self._extract_json_array(text, "biases") or []
            framing = self._extract_json_array(text, "framing") or []
            entities = self._extract_json_array(text, "entities") or []
            tone = self._extract_json_string_value(text, "tone") or "desconocido"
            
            return {
                "facts": facts,
                "unverified_claims": claims,
                "biases": biases,
                "framing": framing,
                "entities": entities,
                "tone": tone
            }

    async def evaluate_topic_specificity(self, topic: str) -> dict:
        """
        Evaluate if a topic is specific enough for a focused analysis.
        Returns: {"is_specific": bool, "reason": str}
        """
        lang_instruction = self._lang_instruction()
        prompt = (
            f"Analyze if the following search topic is SPECIFIC enough to search for concrete news about a recent event, or if it is too generic/ambiguous/broad.\n\n"
            f"Topic: \"{topic}\"\n\n"
            "Rules:\n"
            "1. It is SPECIFIC if it refers to a concrete event, an election, a match in context, a law, a recent controversy, etc. (E.g., \"Catalan election results 2024\", \"Amnesty law approval\", \"Seville Holy Week poster controversy\").\n"
            "2. It is GENERIC if it is a single broad word, an abstract concept, or a topic without a clear temporal or factual context. (E.g., \"Politics\", \"Economy\", \"Football\", \"News\", \"Spain\", \"War\").\n"
            "3. If it is generic, it MUST be rejected.\n\n"
            f"⚠️ LANGUAGE INSTRUCTION: {lang_instruction}\n"
            "Respond ONLY with a valid JSON:\n"
            "{\n"
            "  \"is_specific\": boolean,\n"
            "  \"reason\": \"Brief explanation of why it is specific or why it is too broad (max 1 sentence). If it's broad, suggest what kind of detail is missing.\"\n"
            "}"
        )
        response = await self.analyze(prompt, max_tokens=200)
        
        # Parse response
        try:
            # Clean potential markdown
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            return json.loads(text)
        except Exception as e:
            logger.error("Failed to parse topic specificity response", error=str(e), response=response)
            # Fail safe: assume specific to not block user on error, but log it.
            # Or assume generic? Valid question. Let's assume specific if AI fails to parse, 
            # as it might be a model glitch, but usually broad topics are easy to detect.
            # Actually, user wants strictness. But if JSON fails, we don't know the reason.
            # Let's return is_specific=True to avoid blocking on technical errors, 
            # but usually we'd want to retry. For now, fail open (allow search).
            return {"is_specific": True, "reason": "Error en evaluación, permitiendo búsqueda por defecto."}

    async def generate_search_query(self, title: str, body_preview: str) -> str:
        """
        Generate a semantic search query from an article's headline and body.
        Returns a focused 5-8 word phrase capturing the specific event.
        """
        lang_instruction = "Respond ONLY IN SPANISH." if self.language == "es" else "Respond ONLY IN ENGLISH."
        prompt = (
            f"Headline: {title}\n"
            f"Text: {body_preview[:500]}\n\n"
            "Generate a search phrase of 5 to 8 words that captures the specific EVENT or DEBATE "
            "of this news. DO NOT use names of people or political parties. "
            "Focus on the action, the concrete topic, and the context.\n"
            f"⚠️ LANGUAGE INSTRUCTION: {lang_instruction}\n"
            "Respond ONLY with the phrase, without quotes or explanations."
        )
        result = await self.analyze(prompt, max_tokens=100)
        # Clean up: take just the first line, strip quotes/whitespace
        query = result.strip().split("\n")[0].strip().strip('"').strip("'")
        logger.info("Generated semantic search query", original_title=title[:80], query=query)
        return query

    def _build_analysis_prompt(self, articles: list[dict]) -> str:
        """Build the structured analysis Mega-Prompt."""
        # Only process the first main article to save tokens and avoid multi-article merging
        article = articles[0]
        for a in articles:
            if a.get("role") == "MAIN_SOURCE_TO_ANALYZE":
                article = a
                break

        lang_instruction = self._lang_instruction()
        
        len_map = {
            "short": "Very brief and concise summary of 50-100 words",
            "medium": "Standard summary of 200-300 words",
            "long": "Detailed summary of 400-500 words",
        }
        len_instruction = len_map.get(self.summary_length, len_map["medium"])

        bias_map = {
            "standard": "Detect only obvious biases, clear sensationalism, or markedly subjective words.",
            "strict": "Be extremely meticulous. Detect any minimal unnecessary adjectivation, subtle framing, omission of context, and mild ideological favoritism.",
        }
        bias_instruction = bias_map.get(self.bias_strictness, bias_map["standard"])

        source_name = article.get('source_name', 'Desconocida')
        
        return f"""Analyze the provided news article meticulously. Extract facts, detect biases, and generate a neutralized version of the article.

{lang_instruction}

USER PREFERENCES:
- Length: {len_instruction}
- Bias detection strictness: {bias_instruction}

--- ARTICLE ---
Source: {source_name}
Title: {article.get('title', '')}
Text: {article.get('body', '')[:4000]}

Respond ONLY with valid JSON with this exact structure:

{{
  "topic_summary": "Brief description of the topic in 2-3 sentences",
  "objective_facts": ["fact 1", "fact 2", "fact 3"],
  "opinions_and_hypotheses": ["opinion 1", "speculation 2"],
  "omissions": ["missing context 1"],
  "bias_elements": [
    {{
      "source": "{source_name}",
      "type": "sensationalism|omission|framing|adjectivation",
      "original_text": "exact quote from text",
      "explanation": "logical explanation of why it is a bias",
      "severity": 3
    }}
  ],
  "neutralized_article": {{
    "title": "Concise, factual title without bias. Do not use loaded words.",
    "content": "{len_instruction}. Developed description based EXCLUSIVELY on the objective_facts. Do not repeat the original framing."
  }},
  "source_bias_scores": {{
    "{source_name}": {{"score": 0.5, "direction": "left|center|right", "confidence": 0.7}}
  }}
}}

IMPORTANT: The JSON must be completely valid. Do not include any text outside the JSON."""
