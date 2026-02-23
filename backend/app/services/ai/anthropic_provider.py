"""Anthropic Claude provider implementation."""

import structlog
from anthropic import AsyncAnthropic

from app.services.ai.base import AIProvider

logger = structlog.get_logger()


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "anthropic"

    async def analyze(self, prompt: str, max_tokens: int = 4000) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            system="Eres un analista de medios experto. Responde siempre en JSON válido.",
        )
        return response.content[0].text if response.content else ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Anthropic doesn't have an embeddings API — fall back to local
        raise NotImplementedError("Anthropic does not provide embeddings. Use local sentence-transformers.")

    def validate_key(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-ant-"))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Claude 3.5 Sonnet pricing (approximate)
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost
