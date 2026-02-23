"""OpenAI provider implementation."""

import structlog
from openai import AsyncOpenAI

from app.services.ai.base import AIProvider

logger = structlog.get_logger()


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider (GPT-4o, GPT-4o-mini, etc.)."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "openai"

    async def analyze(self, prompt: str, max_tokens: int = 4000) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "Eres un analista de medios experto. Responde siempre en JSON válido."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in response.data]

    def validate_key(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-"))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # GPT-4o pricing (approximate, may change)
        input_cost = (input_tokens / 1_000_000) * 2.50
        output_cost = (output_tokens / 1_000_000) * 10.00
        return input_cost + output_cost
