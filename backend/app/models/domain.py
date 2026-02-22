"""SQLAlchemy ORM models for the news analysis domain."""

from datetime import datetime

import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base

class ArticleStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    CONTEXTUALIZED = "CONTEXTUALIZED"


class UserAPIKey(Base):
    """Encrypted API keys provided by the user."""

    __tablename__ = "user_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, anthropic, google, ollama
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SearchTask(Base):
    """A user-initiated search or analysis task."""

    __tablename__ = "search_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)  # Topic search
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Direct URL input
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, scraping, analyzing, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    progress_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    articles: Mapped[list["Article"]] = relationship(back_populates="search_task", cascade="all, delete-orphan")
    analysis: Mapped["AnalysisResult | None"] = relationship(back_populates="search_task", uselist=False, cascade="all, delete-orphan")


class Article(Base):
    """A scraped news article."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_task_id: Mapped[int] = mapped_column(ForeignKey("search_tasks.id"), nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)  # "El País", "ABC", etc.
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Topic cluster assignment
    is_source: Mapped[bool] = mapped_column(Boolean, default=False)  # True if this is the user's submitted article
    bias_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0 (neutral) to 1.0 (very biased)
    bias_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Detailed bias breakdown
    trust_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Trust score of the domain at the time of analysis
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # Similarity to the query or centroid
    status: Mapped[ArticleStatus] = mapped_column(Enum(ArticleStatus, native_enum=False, length=20), default=ArticleStatus.DETECTED)
    structural_reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    search_task: Mapped["SearchTask"] = relationship(back_populates="articles")
    structured_facts: Mapped[list["StructuredFact"]] = relationship(back_populates="article", cascade="all, delete-orphan")


class AnalysisResult(Base):
    """The LLM-generated analysis for a search task."""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_task_id: Mapped[int] = mapped_column(ForeignKey("search_tasks.id"), unique=True, nullable=False)
    topic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    objective_facts: Mapped[list] = mapped_column(JSONB, nullable=False)  # List of factual statements
    bias_elements: Mapped[list] = mapped_column(JSONB, nullable=False)  # List of bias detections
    neutralized_summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_bias_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Per-source bias metrics
    provider_used: Mapped[str] = mapped_column(String(50), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filtered_articles_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search_task: Mapped["SearchTask"] = relationship(back_populates="analysis")


class TopicCache(Base):
    """
    Cache for topic specificity checks.
    
    Used to quickly reject broad/generic topics without calling the AI provider
    every time. The system 'learns' which topics are broad.
    """

    __tablename__ = "topic_cache"

    topic_hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA256 of normalized topic
    topic_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_specific: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourceDomain(Base):
    """
    Dynamic Trust Score and Bias representation for news domains.
    Populated on-the-fly when evaluating new sources.
    """

    __tablename__ = "source_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # e.g., "elmundo.es"
    is_evaluated: Mapped[bool] = mapped_column(Boolean, default=False)
    trust_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0 to 100
    bias_lean: Mapped[str | None] = mapped_column(String(50), nullable=True)  # left, center, right, extreme...
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # Why it got this score
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArticleCache(Base):
    """
    Cache for individual article extraction results.
    Prevents re-scraping and re-extracting the same URL if it hasn't expired.
    """
    __tablename__ = "article_cache"

    url_hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA256 of the URL
    url_canonical: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # pgvector column for ANN similarity search
    embedding_vector: Mapped[list | None] = mapped_column(Vector(384), nullable=True) 
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QueryCache(Base):
    """
    Cache for full query and analysis results.
    Prevents running the entire LLM pipeline for the exact same query in a short period.
    """
    __tablename__ = "query_cache"

    query_hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA256 of normalized query
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_result_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_results.id", ondelete="SET NULL"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Feedback(Base):
    """
    User feedback (like/dislike) on analysis results or individual articles.
    """
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'analysis', 'article', 'domain'
    target_id: Mapped[int | str] = mapped_column(String(255), nullable=False, index=True) # ID of target (can be int cast to string or string domain)
    vote: Mapped[str] = mapped_column(String(10), nullable=False)  # 'like', 'dislike', 'neutral'
    session_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StructuredFact(Base):
    """An atomic extracted fact or assertion from an article."""
    
    __tablename__ = "structured_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False) # FACT, UNVERIFIED_CLAIM, BIAS, FRAMING, OMISSION, TONE
    entities: Mapped[list] = mapped_column(JSONB, default=list)
    embedding: Mapped[list | None] = mapped_column(Vector(384), nullable=True) # Assuming all-MiniLM-L6-v2 size mapping
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    article: Mapped["Article"] = relationship(back_populates="structured_facts")


class GeneratedNews(Base):
    """The final synthethized impartial news based exclusively on established facts."""
    
    __tablename__ = "generated_news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    lead: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    context_articles_ids: Mapped[list] = mapped_column(JSONB, nullable=False) # List of integer ids of articles
    reliability_score_achieved: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_new_context_available: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    traces: Mapped[list["FactTraceability"]] = relationship(back_populates="generated_news", cascade="all, delete-orphan")


class FactTraceability(Base):
    """Links paragraphs in GeneratedNews to the core StructuredFacts driving them."""
    
    __tablename__ = "fact_traceability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generated_news_id: Mapped[int] = mapped_column(ForeignKey("generated_news.id", ondelete="CASCADE"), nullable=False, index=True)
    structured_fact_id: Mapped[int] = mapped_column(ForeignKey("structured_facts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    generated_news: Mapped["GeneratedNews"] = relationship(back_populates="traces")
    structured_fact: Mapped["StructuredFact"] = relationship()
