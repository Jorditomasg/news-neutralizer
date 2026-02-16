import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_preview_endpoint_success():
    # Mock ArticleExtractor
    with patch("app.api.routes.search.ArticleExtractor") as MockExtractor:
        mock_instance = MockExtractor.return_value
        mock_instance.extract = AsyncMock(return_value=AsyncMock(
            title="Test Article",
            source_name="Test Source",
            source_url="http://example.com/article",
            author="Test Author",
            published_at="2024-02-16T12:00:00Z",
            topics=["topic1", "topic2"]
        ))
        # The mock return value for extract should be an object with attributes, not a dict
        # Actually ExtractedArticle is a dataclass, so we can mock it or use an object
        from app.services.scraper.extractor import ExtractedArticle
        mock_instance.extract.return_value = ExtractedArticle(
            title="Test Article",
            source_name="Test Source",
            source_url="http://example.com/article",
            author="Test Author",
            published_at=None,
            topics=["topic1", "topic2"],
            body="Test Body"
        )

        response = client.post(
            "/api/v1/search/preview",
            json={"url": "http://example.com/article"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Article"
        assert data["source_name"] == "Test Source"
        assert data["topics"] == ["topic1", "topic2"]

@pytest.mark.asyncio
async def test_preview_endpoint_invalid_url():
    response = client.post(
        "/api/v1/search/preview",
        json={"url": "not-a-url"}
    )
    assert response.status_code == 422
