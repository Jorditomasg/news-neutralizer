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
    neutralized_summary: str
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

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

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
        prompt = (
            "Analiza el siguiente fragmento de texto periodístico y extrae meticulosamente "
            "la información requerida en formato JSON estricto. "
            "Tu análisis debe ser completamente exhaustivo y atómico.\n"
            "⚠️ IMPORTANTE: Si el texto es muy corto o parece estar cortado (ej. muro de pago), "
            "extrae los hechos disponibles por mínimos que sean. NO devuelvas listas vacías si hay al menos un hecho en el texto.\n"
            "⚠️ IMPORTANTE: Si no hay elementos de sesgo, afirmaciones sin verificar o framing, devuelve una lista vacía `[]`. NO devuelvas objetos vacíos como `[{\"type\": \"\", \"quote\": \"\", \"explanation\": \"\"}]`.\n\n"
            f"TEXTO:\n{chunk}\n\n"
            "Responde SOLO con un objeto JSON válido que contenga exactamente estas claves:\n"
            "{\n"
            '  "facts": ["Lista de hechos verificables o acciones concretas ocurridas. Cada uno debe ser una afirmación independiente y atómica."],\n'
            '  "unverified_claims": ["Afirmaciones o citas de fuentes que no son hechos consolidados. Usa [] si no hay ninguna."],\n'
            '  "biases": [\n'
            '    {\n'
            '      "type": "tipo de sesgo (sensacionalismo, adjetivación, victimización, etc.)",\n'
            '      "quote": "cita textual exacta donde se aprecia",\n'
            '      "explanation": "breve explicación"\n'
            '    }\n'
            '  ], // Usa [] si no hay ningún sesgo claro.\n'
            '  "framing": ["Descripción breve de cómo se está enmarcando la noticia. Usa [] si no aplica."],\n'
            '  "entities": ["Lista de nombres propios, organizaciones, cargos o lugares mencionados clave."],\n'
            '  "tone": "Una palabra que defina el tono general (ej. alarmista, neutral, crítico, empático)."\n'
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
            
        facts_text = "\n".join([f"- {f}" for f in facts])
        prompt = (
            "A continuación tienes una lista de hechos extraídos de diferentes fragmentos "
            "de un mismo artículo periodístico. Tu tarea es eliminar duplicados exactos "
            "o redundancias, combinando información si es necesario, para producir una "
            "lista consolidada, atómica y exhaustiva de los hechos.\n\n"
            f"HECHOS ORIGINALES:\n{facts_text}\n\n"
            "Responde SOLO con un objeto JSON válido que contenga la clave 'consolidated_facts' "
            "cuyo valor sea una lista de strings con los hechos consolidados.\n"
            "Ejemplo de formato de respuesta:\n"
            "{\n"
            '  "consolidated_facts": [\n'
            '    "Hecho 1",\n'
            '    "Hecho 2"\n'
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
                neutralized_summary=data.get("neutralized_summary", ""),
                source_bias_scores=data.get("source_bias_scores", {}),
            )
        except json.JSONDecodeError:
            logger.warning("Direct JSON parse failed, using regex extraction")

        # Strategy 2: Extract fields individually with regex (handles truncation)
        topic = self._extract_json_string_value(text, "topic_summary") or ""
        facts = self._extract_json_array(text, "objective_facts") or []
        bias = self._extract_json_array(text, "bias_elements") or []
        summary = self._extract_json_string_value(text, "neutralized_summary") or ""
        scores = self._extract_json_object(text, "source_bias_scores") or {}

        # Check if we got anything useful
        has_content = bool(topic or facts or bias or summary)
        if has_content:
            logger.info(
                "Extracted partial AI response",
                topic_len=len(topic),
                facts_count=len(facts),
                bias_count=len(bias),
                summary_len=len(summary),
                has_scores=bool(scores),
            )
            return AnalysisResult(
                topic_summary=topic,
                objective_facts=facts,
                bias_elements=bias,
                neutralized_summary=summary,
                source_bias_scores=scores,
            )

        # Nothing could be parsed
        logger.error("Could not extract any fields from AI response",
                      response_preview=text[:300])
        return AnalysisResult(
            topic_summary="No se pudo procesar la respuesta de la IA",
            objective_facts=[],
            bias_elements=[],
            neutralized_summary=text[:2000],
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
        prompt = (
            f"Analiza si el siguiente tema de búsqueda es lo suficientemente ESPECÍFICO para buscar noticias concretas sobre un evento reciente, o si es demasiado genérico/ambiguo/amplio.\n\n"
            f"Tema: \"{topic}\"\n\n"
            "Reglas:\n"
            "1. Es ESPECÍFICO si se refiere a un evento concreto, una elección, un partido en un contexto, una ley, una polémica reciente, etc. (Ej: \"Resultados elecciones catalanas 2024\", \"Ley de amnistía aprobación\", \"Polémica cartel Semana Santa Sevilla\").\n"
            "2. Es GENÉRICO si es una sola palabra amplia, un concepto abstracto, o un tema sin contexto temporal o factual claro. (Ej: \"Política\", \"Economía\", \"Fútbol\", \"Noticias\", \"España\", \"Guerra\").\n"
            "3. Si es genérico, DEBE ser rechazado.\n\n"
            "Responde SOLO con un JSON válido:\n"
            "{\n"
            "  \"is_specific\": boolean,\n"
            "  \"reason\": \"Breve explicación de por qué es específico o por qué es demasiado amplio (max 1 frase). Si es amplio, sugiere qué tipo de detalle falta.\"\n"
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
        prompt = (
            f"Titular: {title}\n"
            f"Texto: {body_preview[:500]}\n\n"
            "Genera una frase de búsqueda de 5 a 8 palabras que capture el EVENTO o DEBATE "
            "específico de esta noticia. NO uses nombres de personas ni partidos políticos. "
            "Céntrate en la acción, el tema concreto y el contexto.\n"
            "Responde SOLO con la frase, sin comillas ni explicaciones."
        )
        result = await self.analyze(prompt, max_tokens=100)
        # Clean up: take just the first line, strip quotes/whitespace
        query = result.strip().split("\n")[0].strip().strip('"').strip("'")
        logger.info("Generated semantic search query", original_title=title[:80], query=query)
        return query

    def _build_analysis_prompt(self, articles: list[dict]) -> str:
        """Build the structured analysis prompt."""
        # Limit to 5 articles max to keep context manageable
        limited = articles[:5]
        articles_text = ""
        for i, article in enumerate(limited, 1):
            role = article.get("role", "ARTICLE")
            articles_text += f"\n--- ARTÍCULO {i} [{role}] ---\n"
            articles_text += f"Fuente: {article.get('source_name', 'Desconocida')}\n"
            articles_text += f"Título: {article.get('title', '')}\n"
            articles_text += f"Texto: {article.get('body', '')[:1500]}\n"

        return f"""Analiza estos artículos sobre el mismo tema. Detecta sesgos y redacta un resumen neutral.

INSTRUCCIÓN CRÍTICA:
Si un artículo está marcado como [MAIN_SOURCE_TO_ANALYZE], tu 'topic_summary', 'objective_facts' y 'neutralized_summary' DEBEN centrarse EXCLUSIVAMENTE en la noticia o evento reportado en ese artículo principal.
Los artículos marcados como [RELATED_CONTEXT] solo deben usarse para comparar, detectar qué información omitió el artículo principal, contrastar titulares y calcular el sesgo. 
Bajo NINGUNA circunstancia debes resumir o incluir información de los [RELATED_CONTEXT] que no tenga relación directa y explícita con el evento del [MAIN_SOURCE_TO_ANALYZE]. Si los artículos relacionados hablan de un tema distinto (incluso si son la noticia global del día), IGNÓRALOS por completo y basa tu respuesta solo en el principal.

{articles_text}

Responde SOLO con JSON válido con esta estructura:

{{
  "topic_summary": "Descripción del tema en 2-3 frases centrada en la noticia principal",
  "objective_facts": ["hecho 1", "hecho 2", "hecho 3", "hecho 4", "hecho 5"],
  "bias_elements": [
    {{
      "source": "nombre del medio",
      "type": "sensacionalismo|omisión|framing|adjetivación",
      "original_text": "cita textual breve",
      "explanation": "por qué es sesgo",
      "severity": 3
    }}
  ],
  "neutralized_summary": "Resumen neutral de 200-300 palabras centrado en la noticia principal. Solo hechos verificados, sin opiniones ni adjetivos valorativos. Incluye datos y citas textuales entre comillas.",
  "source_bias_scores": {{
    "nombre del medio": {{"score": 0.5, "direction": "izquierda|centro|derecha", "confidence": 0.7}}
  }}
}}

IMPORTANTE: El JSON debe ser válido. Usa comillas dobles. No incluyas texto fuera del JSON."""
