"""Celery task definitions — pipeline for search and analysis."""

from app.tasks.search_tasks import search_and_analyze, search_and_analyze_url

__all__ = ["search_and_analyze", "search_and_analyze_url"]
