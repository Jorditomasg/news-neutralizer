---
name: fastapi-backend
description: Build production-grade FastAPI backends with async patterns, Pydantic v2 schemas, SQLAlchemy 2.0 async ORM, Celery task queues, and clean architecture. Use when creating API endpoints, database models, background tasks, or service layers.
---

# FastAPI Backend Development

Build robust, async-first Python backends using FastAPI with clean architecture patterns.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py             # pydantic-settings based config
│   ├── api/
│   │   ├── deps.py           # FastAPI dependencies (DB sessions, auth)
│   │   ├── routes/           # One file per resource
│   │   └── websocket/        # WebSocket handlers
│   ├── core/
│   │   ├── security.py       # Encryption, auth utilities
│   │   ├── exceptions.py     # Custom exception hierarchy
│   │   └── middleware.py     # CORS, rate limiting, logging
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic v2 request/response schemas
│   ├── services/             # Business logic layer (no HTTP concerns)
│   └── tasks/                # Celery task definitions
├── alembic/                  # Database migrations
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── test_api/             # API endpoint tests
│   └── test_services/        # Service layer tests
├── pyproject.toml
└── Dockerfile
```

## Key Patterns

### App Factory
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

def create_app() -> FastAPI:
    app = FastAPI(title="News Neutralizer API", lifespan=lifespan)
    app.include_router(api_router, prefix="/api/v1")
    return app
```

### Pydantic v2 Schemas
```python
from pydantic import BaseModel, ConfigDict

class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    source: str
    bias_score: float | None
```

### Async SQLAlchemy 2.0
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Dependency Injection
```python
from fastapi import Depends

async def get_current_user_keys(db: AsyncSession = Depends(get_db)):
    # Decrypt and return user's API keys
    ...

@router.post("/search")
async def search_news(
    query: SearchRequest,
    db: AsyncSession = Depends(get_db),
    keys: UserKeys = Depends(get_current_user_keys),
):
    ...
```

### Celery Tasks
```python
from celery import Celery

celery_app = Celery("worker", broker=settings.REDIS_URL)

@celery_app.task(bind=True, max_retries=3)
def analyze_articles_task(self, task_id: str, articles: list, provider: str, api_key: str):
    try:
        # Heavy processing here
        ...
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
```

## Best Practices

- **Always use async**: All DB queries, HTTP calls, and I/O should be async
- **Pydantic for everything**: Request validation, response serialization, config
- **Dependency injection**: Use `Depends()` for DB sessions, auth, and service instances
- **Service layer**: Keep route handlers thin — business logic lives in `services/`
- **Structured logging**: Use `structlog` with JSON output, redact secrets
- **Error handling**: Global exception handler; never expose internal errors to client
- **Health checks**: `/health` (liveness) and `/ready` (readiness) endpoints
- **Migrations**: Always use Alembic; never modify DB schema manually

## Testing

```bash
pytest --asyncio-mode=auto -v
```

- Use `httpx.AsyncClient` for API tests
- Use `pytest-asyncio` for async test functions
- Mock external services (LLM APIs, scrapers) with `unittest.mock`
