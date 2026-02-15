"""Ollama local provider implementation (no API key required)."""

import structlog
import httpx

from app.services.ai.base import AIProvider

logger = structlog.get_logger()


class OllamaProvider(AIProvider):
    """Ollama local model provider (self-hosted, no API key)."""

    def __init__(self, api_key: str | None = None, model: str = "llama3.1", base_url: str = "http://localhost:11434"):
        super().__init__(api_key)
        self._model = model
        self._base_url = base_url

    @property
    def name(self) -> str:
        return "ollama"

    async def analyze(self, prompt: str, max_tokens: int = 4000) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": f"Responde en JSON válido.\n\n{prompt}",
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.3,
                    },
                },
            )
            response.raise_for_status()
            return response.json().get("response", "")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
                response.raise_for_status()
                embeddings.append(response.json().get("embedding", []))
        return embeddings

    def validate_key(self) -> bool:
        # Ollama doesn't need an API key
        return True

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Local model — no API cost
        return 0.0
