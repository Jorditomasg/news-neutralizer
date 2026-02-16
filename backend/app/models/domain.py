"""SQLAlchemy ORM models for the news analysis domain."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


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
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search_task: Mapped["SearchTask"] = relationship(back_populates="articles")


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
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search_task: Mapped["SearchTask"] = relationship(back_populates="analysis")
