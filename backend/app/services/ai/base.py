"""Abstract base class for AI providers (Strategy Pattern)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    """Structured result from AI analysis."""

    topic_summary: str
    objective_facts: list[str]
    bias_elements: list[dict]
    neutralized_summary: str
    source_bias_scores: dict[str, dict]
    tokens_used: int | None = None


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

    async def analyze_articles(self, articles: list[dict]) -> AnalysisResult:
        """
        Analyze a set of articles for bias and generate a neutralized summary.
        Uses a structured prompt and parses the JSON response.
        """
        import json

        prompt = self._build_analysis_prompt(articles)
        response = await self.analyze(prompt, max_tokens=4000)

        # Parse JSON from the response
        try:
            # Try to extract JSON from possible markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            data = json.loads(json_str)

            return AnalysisResult(
                topic_summary=data.get("topic_summary", ""),
                objective_facts=data.get("objective_facts", []),
                bias_elements=data.get("bias_elements", []),
                neutralized_summary=data.get("neutralized_summary", ""),
                source_bias_scores=data.get("source_bias_scores", {}),
            )
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            # Fallback: return raw response as summary
            return AnalysisResult(
                topic_summary="Error parsing AI response",
                objective_facts=[],
                bias_elements=[],
                neutralized_summary=response[:2000],
                source_bias_scores={},
            )

    def _build_analysis_prompt(self, articles: list[dict]) -> str:
        """Build the structured analysis prompt."""
        articles_text = ""
        for i, article in enumerate(articles, 1):
            articles_text += f"\n--- ARTÍCULO {i} ---\n"
            articles_text += f"Fuente: {article.get('source_name', 'Desconocida')}\n"
            articles_text += f"Título: {article.get('title', '')}\n"
            articles_text += f"Texto: {article.get('body', '')[:3000]}\n"

        return f"""Eres un analista de medios experto en detectar sesgo informativo.

Analiza los siguientes artículos sobre el mismo tema y genera un informe estructurado.

{articles_text}

Genera un JSON con esta estructura exacta:
{{
  "topic_summary": "Resumen del tema en 1-2 frases",
  "objective_facts": [
    "Hecho verificable 1",
    "Hecho verificable 2"
  ],
  "bias_elements": [
    {{
      "source": "nombre del medio",
      "type": "sensacionalismo|omisión|framing|adjetivación|falacia",
      "original_text": "texto original del artículo",
      "explanation": "por qué es sesgo y no información factual",
      "severity": 1
    }}
  ],
  "neutralized_summary": "Resumen basado exclusivamente en hechos verificables, sin adjetivos valorativos ni framing editorial",
  "source_bias_scores": {{
    "nombre_medio": {{
      "score": 0.5,
      "direction": "izquierda|centro|derecha|sensacionalista",
      "confidence": 0.8
    }}
  }}
}}

IMPORTANTE:
- Responde SOLO con el JSON, sin texto adicional.
- Sé riguroso: distingue entre hechos verificables y opiniones presentadas como hechos.
- Para severity, usa 1 (mínimo) a 5 (máximo).
- Para score, usa 0.0 (sin sesgo) a 1.0 (sesgo extremo).
"""
