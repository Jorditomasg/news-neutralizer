"""Ollama local provider implementation (no API key required).

Connects to the Ollama Docker service. On first use, automatically
pulls the configured model if it isn't already available.
"""

import structlog
import httpx

from app.services.ai.base import AIProvider

logger = structlog.get_logger()


class OllamaProvider(AIProvider):
    """Ollama local model provider (self-hosted, no API key)."""

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        from app.config import settings
        self._model = model or settings.ollama_model
        self._base_url = base_url or settings.ollama_url

    @property
    def name(self) -> str:
        return "ollama"

    async def _ensure_model(self):
        """Pull the model if it's not already available."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(f"{self._base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    # Check if model is already pulled (exact or with :latest)
                    if self._model in models or f"{self._model}:latest" in models:
                        return
            except httpx.HTTPError:
                pass

        # Model not found — pull it (this can take minutes on first run)
        logger.info("Pulling Ollama model", model=self._model)
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/pull",
                json={"name": self._model, "stream": False},
            )
            resp.raise_for_status()
        logger.info("Model pulled successfully", model=self._model)

    async def analyze(self, prompt: str, max_tokens: int = 4000) -> str:
        await self._ensure_model()
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": f"Responde ÚNICAMENTE con JSON válido, sin texto adicional antes ni después.\n\n{prompt}",
                    "stream": False,
                    "options": {
                        "num_ctx": 32768,
                        "num_predict": max_tokens,
                        "temperature": 0.3,
                    },
                },
            )
            response.raise_for_status()
            return response.json().get("response", "")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        await self._ensure_model()
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
