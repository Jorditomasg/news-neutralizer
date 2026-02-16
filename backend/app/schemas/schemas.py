"""Pydantic v2 schemas for API request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# ── Requests ──────────────────────────────────────────────────

class SearchRequest(BaseModel):
    """Search for news by topic."""
    query: str = Field(..., min_length=3, max_length=500, description="Search topic or keywords")
    sources: list[str] | None = Field(None, description="Specific sources to search (None = all)")


class ExtractArticleRequest(BaseModel):
    """Extract and preview a single article from a URL."""
    url: HttpUrl = Field(..., description="URL of the news article to extract")


class CrossReferenceRequest(BaseModel):
    """Search for related articles after previewing an extracted article."""
    article_id: int = Field(..., description="ID of the previously extracted article")
    topics: list[str] = Field(..., min_length=1, description="Topics to search across sources")
    sources: list[str] | None = Field(None, description="Specific sources to search (None = all)")


class APIKeyCreate(BaseModel):
    """Save a user's API key for an AI provider."""
    provider: str = Field(..., pattern=r"^(openai|anthropic|google|ollama)$")
    api_key: str = Field(..., min_length=1, max_length=500)


# ── Responses ─────────────────────────────────────────────────

class ArticlePreview(BaseModel):
    """Preview of an extracted article (shown before cross-reference search)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_name: str
    source_url: str
    author: str | None
    published_at: datetime | None
    body_preview: str = Field(description="First ~500 chars of the body")
    detected_topics: list[str] = Field(description="Auto-extracted topics/keywords")


class ArticlePreviewResponse(BaseModel):
    """Metadata preview of an article from URL."""
    title: str
    source_name: str
    source_url: str
    author: str | None = None
    published_at: datetime | None = None
    topics: list[str] = []



class ArticleOut(BaseModel):
    """Full article in results."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_name: str
    source_url: str
    author: str | None
    published_at: datetime | None
    body: str
    bias_score: float | None
    bias_details: dict | None
    cluster_id: int | None


class BiasElement(BaseModel):
    """A single detected bias element."""
    source: str
    type: str  # sensacionalismo, omisión, framing, adjetivación, falacia
    original_text: str
    explanation: str
    severity: int = Field(ge=1, le=5)


class SourceBiasScore(BaseModel):
    """Bias score for a single source."""
    score: float = Field(ge=0.0, le=1.0)
    direction: str  # izquierda, centro, derecha, sensacionalista
    confidence: float = Field(ge=0.0, le=1.0)


class AnalysisResultOut(BaseModel):
    """Full analysis result."""
    model_config = ConfigDict(from_attributes=True)

    topic_summary: str
    objective_facts: list[str]
    bias_elements: list[BiasElement]
    neutralized_summary: str
    source_bias_scores: dict[str, SourceBiasScore]
    provider_used: str
    tokens_used: int | None


class SearchTaskOut(BaseModel):
    """Search task status and results."""
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    status: str
    progress: int
    query: str | None
    source_url: str | None
    created_at: datetime
    completed_at: datetime | None
    articles: list[ArticleOut] = []
    analysis: AnalysisResultOut | None = None


class TaskCreated(BaseModel):
    """Response when a new search task is created."""
    task_id: str
    message: str = "Task created successfully"


class APIKeyOut(BaseModel):
    """Confirmation that an API key was saved (never expose the key itself)."""
    provider: str
    is_valid: bool
    created_at: datetime


class AvailableSource(BaseModel):
    """A news source available for searching."""
    name: str
    slug: str
    country: str
    type: str  # rss, web
    enabled: bool = True
