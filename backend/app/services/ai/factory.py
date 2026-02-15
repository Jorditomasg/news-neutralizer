"""AI Provider Factory — creates the right provider from a name + key."""

from app.services.ai.base import AIProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.google_provider import GoogleProvider
from app.services.ai.ollama_provider import OllamaProvider


class AIProviderFactory:
    """
    Factory for creating AI provider instances.

    Usage:
        provider = AIProviderFactory.get("openai", api_key="sk-...")
        result = await provider.analyze_articles(articles)
    """

    _providers: dict[str, type[AIProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "ollama": OllamaProvider,
    }

    @classmethod
    def get(cls, provider_name: str, api_key: str | None = None) -> AIProvider:
        """Get a provider instance by name."""
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unknown provider '{provider_name}'. Available: {available}")
        return provider_class(api_key=api_key)

    @classmethod
    def register(cls, name: str, provider_class: type[AIProvider]) -> None:
        """Register a new provider (for extensibility)."""
        cls._providers[name] = provider_class

    @classmethod
    def available_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())
