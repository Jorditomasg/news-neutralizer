"""Custom exception hierarchy."""

from fastapi import HTTPException, status


class NewsNeutralizerError(Exception):
    """Base exception for application errors."""


class ScrapingError(NewsNeutralizerError):
    """Raised when article scraping fails."""


class AIProviderError(NewsNeutralizerError):
    """Raised when an AI provider call fails."""


class InvalidAPIKeyError(NewsNeutralizerError):
    """Raised when a user's API key is invalid."""


class ArticleExtractionError(NewsNeutralizerError):
    """Raised when article content cannot be extracted from a URL."""


# ── HTTP exceptions (for use in routes) ──────────────────────

def api_key_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="API key required. Configure your AI provider keys in Settings.",
    )


def provider_unavailable(provider: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"AI provider '{provider}' is temporarily unavailable.",
    )
