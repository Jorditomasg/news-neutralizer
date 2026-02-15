---
name: docker-compose
description: Build containerized multi-service applications with Docker and docker-compose. Use when creating Dockerfiles, docker-compose configurations, health checks, multi-stage builds, and container orchestration.
---

# Docker & Docker Compose Development

Build production-ready containerized applications with proper security, performance, and reliability.

## Multi-Stage Dockerfile (Python Backend)

```dockerfile
# Stage 1: Dependencies
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime
FROM python:3.12-slim AS runtime
RUN addgroup --system app && adduser --system --group app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY ./app ./app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Multi-Stage Dockerfile (Next.js Frontend)

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER app
EXPOSE 3000
CMD ["node", "server.js"]
```

## Docker Compose Structure

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/news
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/news
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - api
      - redis
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=news
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d news"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
```

## Best Practices

- **Multi-stage builds**: Minimize image size, separate build and runtime
- **Non-root user**: Always run as non-root in production containers
- **Health checks**: Every service must have health checks
- **Dependency ordering**: Use `depends_on` with `condition: service_healthy`
- **.dockerignore**: Exclude `node_modules`, `__pycache__`, `.git`, `.env`
- **Named volumes**: For persistent data (PostgreSQL)
- **Environment variables**: Use `.env` files for dev, secrets manager for prod
- **Image tagging**: Always tag images with version, not just `latest`
- **Restart policy**: `unless-stopped` for production services

## Development vs Production

- Use `docker-compose.dev.yml` override for:
  - Volume mounts for hot-reload
  - Debug ports
  - Relaxed security settings
- Use `docker-compose.yml` (base) for:
  - Production-ready configuration
  - Strict health checks
  - Resource limits
