"""Google Generative AI (Gemini) provider implementation."""

import structlog
import google.generativeai as genai

from app.services.ai.base import AIProvider

logger = structlog.get_logger()


class GoogleProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        if api_key:
            genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    @property
    def name(self) -> str:
        return "google"

    async def analyze(self, prompt: str, max_tokens: int = 4000) -> str:
        response = await self._model.generate_content_async(
            f"Responde en JSON válido.\n\n{prompt}",
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )
        return response.text if response.text else ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=texts,
        )
        return result["embedding"] if isinstance(result["embedding"][0], list) else [result["embedding"]]

    def validate_key(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Gemini 2.0 Flash pricing (very affordable)
        input_cost = (input_tokens / 1_000_000) * 0.075
        output_cost = (output_tokens / 1_000_000) * 0.30
        return input_cost + output_cost
