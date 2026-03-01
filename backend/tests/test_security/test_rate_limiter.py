import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_rate_limiter():
    """Test that the SlowAPI rate limiter actually kicks in after 30 requests."""
    # We use ASGITransport to hit the FastAPI app directly for tests
    # Wait, the rate limit is 30/minute, so we need to make 31 requests.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for _ in range(30):
            response = await ac.post("/api/v1/auth/session", json={})
            # If rate limiter applies to /health, it will block on 31
            # Actually our global limit applies to all routes?
            # Oh wait, slowapi requires @limiter.limit() on routes, 
            # OR global limit if we configure it correctly. Let's send a request and see if it passes.
            assert response.status_code == 200

        # The 31st request from the same IP should be blocked with 429
        response = await ac.post("/api/v1/auth/session", json={})
        assert response.status_code == 429
        data = response.json()
        assert "Rate limit exceeded" in data.get("detail", "") or "Rate limit" in data.get("error", "") or "Rate limit" in str(data)
